import json

import pytest

from generator import CategoryModel, generate_test_cases, generate_with_model
from generator.classifier import MODEL_PATH
from generator.generate import main

RESET_PASSWORD = {
    "key": "SHOP-1",
    "title": "Reset password",
    "description": "As a user, I want to reset my password so that I can log in again.",
    "acceptance_criteria": [
        "The user receives a reset link by email",
        "The new password must be at least 8 characters",
    ],
}


class FakePipeline:
    """Stands in for the scikit-learn pipeline: picks a category from a keyword."""

    classes_ = ["boundary", "functional", "security"]

    def predict_proba(self, sentences):
        rows = []
        for sentence in sentences:
            if "at least" in sentence:
                rows.append([0.9, 0.05, 0.05])
            elif "admin" in sentence:
                rows.append([0.3, 0.3, 0.4])
            else:
                rows.append([0.1, 0.8, 0.1])
        return rows


def test_predict_gives_category_and_confidence_per_criterion():
    model = CategoryModel(FakePipeline())
    assert model.predict(RESET_PASSWORD["acceptance_criteria"]) == [("functional", 0.8), ("boundary", 0.9)]
    assert model.predict([]) == []


def test_generate_with_model_matches_hand_typed_categories():
    from_model = generate_with_model([RESET_PASSWORD], CategoryModel(FakePipeline()))
    assert from_model == generate_test_cases(RESET_PASSWORD, ["functional", "boundary"])


def test_model_with_unknown_categories_is_rejected():
    class Odd(FakePipeline):
        classes_ = ["functional", "speed"]

    with pytest.raises(ValueError, match="unknown categories"):
        CategoryModel(Odd())


def test_missing_model_file_gives_a_clear_error(tmp_path):
    with pytest.raises(ValueError, match="AI model was not found"):
        CategoryModel.load(tmp_path / "model.pkl")


def test_script_uses_the_model_when_no_categories_are_given(tmp_path, monkeypatch, capsys):
    stories = tmp_path / "stories.json"
    stories.write_text(json.dumps([RESET_PASSWORD, dict(RESET_PASSWORD, key="SHOP-9",
                                   acceptance_criteria=["Only admins can delete products"])]), encoding="utf-8")
    output = tmp_path / "out.json"
    monkeypatch.setattr(CategoryModel, "load", classmethod(lambda cls, path=None: cls(FakePipeline())))

    assert main([str(stories), "--output", str(output)]) == 0
    printed = capsys.readouterr().out
    assert "SHOP-1: The new password must be at least 8 characters -> boundary (0.90)" in printed
    assert "SHOP-9: Only admins can delete products -> security (0.40)  <- low confidence" in printed
    types = [tc["type"] for tc in json.loads(output.read_text(encoding="utf-8"))]
    assert set(types) == {"functional", "boundary", "security"}


def test_script_reports_a_missing_model(tmp_path, capsys):
    stories = tmp_path / "stories.json"
    stories.write_text(json.dumps([RESET_PASSWORD]), encoding="utf-8")
    assert main([str(stories), "--model", str(tmp_path / "none.pkl"), "--output", str(tmp_path / "o.json")]) == 1
    assert "AI model was not found" in capsys.readouterr().err


@pytest.mark.skipif(not MODEL_PATH.is_file(), reason="model/model.pkl not trained yet")
def test_real_model_classifies_the_example_criteria():
    pytest.importorskip("sklearn")
    predictions = CategoryModel.load().predict([
        "The new password must be at least 8 characters",
        "The login page loads in under 2 seconds",
    ])
    assert [category for category, _ in predictions] == ["boundary", "performance"]
    assert all(0 < confidence <= 1 for _, confidence in predictions)


# --- classifier audit (11 Nov 2026) --------------------------------------------------------

from generator.classifier import clean_criterion  # noqa: E402


@pytest.mark.parametrize("raw, cleaned", [
    ("AC1: The page loads fast", "The page loads fast"),
    ("1. The password is hashed", "The password is hashed"),
    ("-   Only admins   can delete", "Only admins can delete"),
    ("[ ] Users can export", "Users can export"),
    ("Version 2 is shown", "Version 2 is shown"),
])
def test_jira_list_markers_are_removed_before_classifying(raw, cleaned):
    assert clean_criterion(raw) == cleaned


class Functional(FakePipeline):
    """Always 'functional' first, 'boundary' second."""

    def predict_proba(self, sentences):
        return [[0.3, 0.6, 0.1] for _ in sentences]


@pytest.mark.parametrize("criterion, category", [
    ("The reset link expires after 30 minutes", "boundary"),      # a time window is a limit
    ("A discount cannot exceed 70% of the price", "boundary"),
    ("The page loads in under 2 seconds", "functional"),           # speed: left to the model
    ("The user receives a reset link by email", "functional"),     # no limit
])
def test_numeric_limits_turn_functional_into_boundary(criterion, category):
    predicted, confidence = CategoryModel(Functional()).predict([criterion])[0]
    assert predicted == category
    assert confidence == (0.3 if category == "boundary" else 0.6)   # always the model's own probability


def test_limit_rule_never_overrides_other_categories():
    assert CategoryModel(FakePipeline()).predict(["Only admins can delete 5 products"])[0][0] == "security"


@pytest.mark.skipif(not MODEL_PATH.is_file(), reason="model/model.pkl not trained")
def test_trained_model_keeps_the_words_that_decide_the_category():
    import joblib
    pipeline = joblib.load(MODEL_PATH)
    words = dict(pipeline.named_steps["features"].transformer_list)["words"]
    assert words.stop_words is None   # "only", "not", "at least", "within" ... must reach the model
    assert {"only", "not", "least", "within"} <= set(words.vocabulary_)
    assert {"%", "$", "8"} <= set(words.build_analyzer()("at most 8 characters, 80% or $50"))


@pytest.mark.skipif(not MODEL_PATH.is_file(), reason="model/model.pkl not trained")
def test_trained_model_on_the_jira_benchmark():
    import csv
    from pathlib import Path
    rows = list(csv.DictReader((Path(MODEL_PATH).parent.parent / "data" / "jira_benchmark.csv").open(encoding="utf-8")))
    predictions = CategoryModel.load().predict([row["text"] for row in rows])
    accuracy = sum(p[0] == row["category"] for p, row in zip(predictions, rows)) / len(rows)
    assert accuracy >= 0.83, accuracy      # 0.858 when trained; the old model scored 0.808
    assert CategoryModel.load().predict(["Only admins can delete products"])[0][0] == "security"
