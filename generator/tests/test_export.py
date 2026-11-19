import csv
import json
from pathlib import Path

import openpyxl
import pytest

from generator import (
    ALL_FIELDS,
    OPTIONAL_FIELDS,
    TEST_CASE_FIELDS,
    deduplicate_test_cases,
    generate_test_cases,
    to_csv,
    to_excel,
    to_gherkin,
    to_gherkin_feature,
    to_xray_json,
)
from generator.generate import main

STORY = {
    "key": "SHOP-1",
    "title": "Reset password",
    "description": "As a user, I want to reset my password so that I can log in again.",
    "acceptance_criteria": [
        "The user receives a reset link by email",
        "The new password must be at least 8 characters",
    ],
}


def test_optional_attributes_omitted_by_default():
    test_cases = generate_test_cases(STORY, ["functional", "boundary"])
    for tc in test_cases:
        assert tuple(tc) == TEST_CASE_FIELDS
        for opt in OPTIONAL_FIELDS:
            assert opt not in tc


def test_optional_attributes_included_when_flag_is_true():
    test_cases = generate_test_cases(STORY, ["functional", "boundary"], include_optional=True)
    for tc in test_cases:
        assert tuple(tc) == ALL_FIELDS
        assert tc["priority"] in ("Critical", "High", "Medium", "Low")
        assert isinstance(tc["preconditions"], list) and tc["preconditions"]
        assert isinstance(tc["execution_type"], str) and tc["execution_type"]
        assert "Scenario:" in tc["gherkin"]
        assert "Given " in tc["gherkin"]
        assert "Then " in tc["gherkin"]


def test_deduplicate_removes_identical_test_cases():
    story_with_duplicates = {
        "key": "SHOP-1",
        "title": "Reset password",
        "description": "As a user, I want to reset my password so that I can log in again.",
        "acceptance_criteria": [
            "The email address must be valid",
            "The email address must be valid",
        ],
    }
    raw = generate_test_cases(story_with_duplicates, ["validation", "validation"], deduplicate=False)
    assert len(raw) == 6
    deduped = generate_test_cases(story_with_duplicates, ["validation", "validation"], deduplicate=True)
    assert len(deduped) == 3
    assert [tc["id"] for tc in deduped] == ["SHOP-1-TC1", "SHOP-1-TC2", "SHOP-1-TC3"]


def test_to_csv_output():
    test_cases = generate_test_cases(STORY, ["functional", "boundary"], include_optional=True)
    csv_text = to_csv(test_cases)
    reader = list(csv.reader(csv_text.splitlines()))
    assert reader[0][0] == "Story Key"
    assert "Priority" in reader[0]
    assert len(reader) == len(test_cases) + 1
    assert reader[1][0] == "SHOP-1"


def test_to_excel_output(tmp_path: Path):
    test_cases = generate_test_cases(STORY, ["functional", "boundary"], include_optional=True)
    file_path = tmp_path / "test_cases.xlsx"
    to_excel(test_cases, file_path)
    assert file_path.exists()
    wb = openpyxl.load_workbook(file_path)
    ws = wb.active
    assert ws["A1"].value == "Story Key"
    assert ws.max_row == len(test_cases) + 1


def test_to_gherkin_feature():
    test_cases = generate_test_cases(STORY, ["functional", "boundary"])
    feature_text = to_gherkin_feature(STORY, test_cases)
    assert feature_text.startswith("Feature: Reset password")
    assert "Scenario:" in feature_text
    assert "Given Open the reset password page" in feature_text


def test_to_xray_json():
    test_cases = generate_test_cases(STORY, ["functional", "boundary"], include_optional=True)
    xray_text = to_xray_json(test_cases)
    data = json.loads(xray_text)
    assert "tests" in data
    assert len(data["tests"]) == len(test_cases)
    first = data["tests"][0]
    assert first["testKey"] == "SHOP-1-TC1"
    assert "summary" in first["info"]
    assert "steps" in first


def test_cli_optional_and_export_formats(tmp_path: Path):
    stories_file = tmp_path / "stories.json"
    stories_file.write_text(json.dumps([STORY]), encoding="utf-8")
    categories_file = tmp_path / "cats.json"
    categories_file.write_text(json.dumps({"SHOP-1": ["functional", "boundary"]}), encoding="utf-8")

    csv_out = tmp_path / "output.csv"
    code = main([str(stories_file), "--categories", str(categories_file), "--output", str(csv_out), "--format", "csv", "--optional"])
    assert code == 0
    assert csv_out.exists() and "Priority" in csv_out.read_text(encoding="utf-8")

    xlsx_out = tmp_path / "output.xlsx"
    code = main([str(stories_file), "--categories", str(categories_file), "--output", str(xlsx_out), "--format", "excel"])
    assert code == 0
    assert xlsx_out.exists() and xlsx_out.stat().st_size > 0
