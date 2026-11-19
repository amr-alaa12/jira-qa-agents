import json
import pytest

from generator import CategoryModel, SelfMadeClassifier, generate_test_cases, generate_with_model
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


class FakeClassifier:
    classes_ = ["BOUNDARY", "FUNCTIONAL", "MAINTAINABILITY", "PERFORMANCE",
                "PORTABILITY", "RELIABILITY", "SECURITY", "USABILITY", "VALIDATION"]

    def predict_proba(self, features):
        rows = []
        for _ in range(features.shape[0] if hasattr(features, 'shape') else len(features)):
            rows.append([0.02, 0.8, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.06])
        return rows


class FakeVectorizer:
    class _FakeMatrix:
        def __init__(self, n):
            self.shape = (n, 100)

        def __len__(self):
            return self.shape[0]

    def transform(self, texts):
        return self._FakeMatrix(len(texts))


class FakeClassifierWithKeywords(FakeClassifier):
    def predict_proba(self, sentences):
        rows = []
        for sentence in sentences:
            text = sentence if isinstance(sentence, str) else ""
            if "at least" in text:
                rows.append([0.9, 0.02, 0.01, 0.01, 0.01, 0.01, 0.02, 0.01, 0.01])
            elif "admin" in text:
                rows.append([0.05, 0.05, 0.01, 0.01, 0.01, 0.01, 0.8, 0.05, 0.01])
            elif "recover" in text or "failover" in text:
                rows.append([0.01, 0.02, 0.01, 0.01, 0.01, 0.9, 0.02, 0.01, 0.01])
            elif "portable" in text or "cross-platform" in text:
                rows.append([0.01, 0.02, 0.01, 0.01, 0.9, 0.01, 0.02, 0.01, 0.01])
            elif "maintain" in text or "modular" in text:
                rows.append([0.01, 0.02, 0.9, 0.01, 0.01, 0.01, 0.02, 0.01, 0.01])
            else:
                rows.append([0.05, 0.8, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.01])
        return rows


def test_self_made_classifier_works_standalone():
    clf = SelfMadeClassifier()
    assert clf.predict(["The password must be at least 8 characters"]) == ["boundary"]
    assert clf.predict(["The page loads in under 2 seconds"]) == ["performance"]
    assert clf.predict(["Only admins can delete products"]) == ["security"]
    assert clf.predict(["The email must be valid"]) == ["validation"]
    assert clf.predict(["System must recover after crash"]) == ["reliability"]
    assert clf.predict(["Works across browsers like Chrome and Safari"]) == ["portability"]
    assert clf.predict(["Config settings can be changed easily"]) == ["maintainability"]
    assert clf.predict(["The UI is user-friendly and accessible"]) == ["usability"]
    assert clf.predict(["User receives an email"]) == ["functional"]


def test_predict_gives_category_and_confidence_per_criterion():
    model = CategoryModel(FakeClassifierWithKeywords())
    result = model.predict(RESET_PASSWORD["acceptance_criteria"])
    assert result == [("functional", 0.8), ("boundary", 0.9)]
    assert model.predict([]) == []


def test_predict_with_separate_vectorizer():
    model = CategoryModel(FakeClassifier(), FakeVectorizer())
    result = model.predict(RESET_PASSWORD["acceptance_criteria"])
    assert result == [("functional", 0.8), ("functional", 0.8)]
    assert model.predict([]) == []


def test_generate_with_model_matches_hand_typed_categories():
    from_model = generate_with_model(
        [RESET_PASSWORD], CategoryModel(FakeClassifierWithKeywords())
    )
    assert from_model == generate_test_cases(RESET_PASSWORD, ["functional", "boundary"])


def test_model_with_unknown_categories_is_rejected():
    class Odd(FakeClassifier):
        classes_ = ["functional", "speed"]

    with pytest.raises(ValueError, match="unknown categories"):
        CategoryModel(Odd())


def test_uppercase_classes_are_accepted():
    model = CategoryModel(FakeClassifier())
    assert "functional" in model._classes
    assert "FUNCTIONAL" not in model._classes


def test_missing_model_file_falls_back_to_self_made_classifier(tmp_path):
    model = CategoryModel.load(tmp_path / "model.pkl")
    assert isinstance(model._classifier, SelfMadeClassifier)


def test_script_uses_the_model_when_no_categories_are_given(tmp_path, monkeypatch, capsys):
    stories = tmp_path / "stories.json"
    stories.write_text(json.dumps([RESET_PASSWORD, dict(RESET_PASSWORD, key="SHOP-9",
                                   acceptance_criteria=["Only admins can delete products"])]), encoding="utf-8")
    output = tmp_path / "out.json"
    monkeypatch.setattr(
        CategoryModel, "load",
        classmethod(lambda cls, path=None, vectorizer_path=None: cls(FakeClassifierWithKeywords()))
    )

    assert main([str(stories), "--output", str(output)]) == 0
    printed = capsys.readouterr().out
    assert "SHOP-1: The new password must be at least 8 characters -> boundary (0.90)" in printed
    assert "SHOP-9: Only admins can delete products -> security (0.80)" in printed
    types = [tc["type"] for tc in json.loads(output.read_text(encoding="utf-8"))]
    assert set(types) == {"functional", "boundary", "security"}


@pytest.mark.skipif(not MODEL_PATH.is_file(), reason="model/ai_classifier_model.pkl not trained yet")
def test_real_model_classifies_the_example_criteria():
    pytest.importorskip("sklearn")
    model = CategoryModel.load()
    predictions = model.predict([
        "The new password must be at least 8 characters",
        "The login page loads in under 2 seconds",
    ])
    assert all(0 < confidence <= 1 for _, confidence in predictions)
    from generator.core import CATEGORIES
    assert all(category in CATEGORIES for category, _ in predictions)
