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
    to_cypress_ts,
    to_excel,
    to_gherkin,
    to_gherkin_feature,
    to_playwright_python,
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


def test_to_playwright_python():
    test_cases = generate_test_cases(STORY, ["functional", "boundary"])
    code = to_playwright_python(STORY, test_cases)
    assert "from playwright.sync_api import Page, expect" in code
    assert "def test_shop_1_tc1_" in code
    assert "page.goto" in code
    assert "expect(page.locator" in code


def test_to_cypress_ts():
    test_cases = generate_test_cases(STORY, ["functional", "boundary"])
    code = to_cypress_ts(STORY, test_cases)
    assert "describe('SHOP-1: Reset password'" in code
    assert "it('SHOP-1-TC1:" in code
    assert "cy.visit" in code
    assert "cy.get" in code


def test_cli_playwright_and_cypress_formats(tmp_path: Path):
    stories_file = tmp_path / "stories.json"
    stories_file.write_text(json.dumps([STORY]), encoding="utf-8")
    categories_file = tmp_path / "cats.json"
    categories_file.write_text(json.dumps({"SHOP-1": ["functional", "boundary"]}), encoding="utf-8")

    pw_out = tmp_path / "test_spec.py"
    code = main([str(stories_file), "--categories", str(categories_file), "--output", str(pw_out), "--format", "playwright"])
    assert code == 0
    assert pw_out.exists() and "from playwright.sync_api" in pw_out.read_text(encoding="utf-8")

    cy_out = tmp_path / "test.cy.ts"
    code = main([str(stories_file), "--categories", str(categories_file), "--output", str(cy_out), "--format", "cypress"])
    assert code == 0
    assert cy_out.exists() and "describe('SHOP-1" in cy_out.read_text(encoding="utf-8")


def test_smart_preconditions_extraction():
    story_cond = {
        "key": "SHOP-9",
        "title": "Discount rule",
        "description": "As a customer, I want discounts.",
        "acceptance_criteria": [
            "When the cart exceeds $100, free shipping is applied",
            "Given an expired token, access is forbidden",
            "After 3 failed login attempts, the account is locked",
        ],
    }
    cases = generate_test_cases(story_cond, ["functional", "security", "security"], include_optional=True)
    c1_pre = cases[0]["preconditions"]
    assert any("Cart exceeds $100" in p for p in c1_pre)
    c2_pre = cases[3]["preconditions"]
    assert any("Expired token is active" in p for p in c2_pre)
    c3_pre = cases[6]["preconditions"]
    assert any("3 failed login attempts have occurred" in p for p in c3_pre)


def test_security_injection_fuzz_drafts():
    story_sec = {
        "key": "SEC-1",
        "title": "Search security",
        "description": "As a user, I want search input to be safe.",
        "acceptance_criteria": [
            "The search query must prevent SQL injection and sanitize special characters",
        ],
    }
    cases = generate_test_cases(story_sec, ["security"])
    titles = [c["title"] for c in cases]
    inputs = [c["input"] for c in cases]
    assert any("SQL injection" in t for t in titles)
    assert any("Cross-site scripting (XSS)" in t for t in titles)
    assert any("' OR '1'='1" in inp for inp in inputs)
    assert any("<script>alert(1)</script>" in inp for inp in inputs)


def test_new_field_kinds_validation():
    story_ip = {
        "key": "NET-1",
        "title": "IP Whitelist",
        "description": "As an admin, I want to whitelist IP addresses.",
        "acceptance_criteria": [
            "The IP address must be valid",
            "The domain name must be valid",
            "The SSN must be valid",
        ],
    }
    cases = generate_test_cases(story_ip, ["validation", "validation", "validation"])
    inputs = [c["input"] for c in cases]
    assert any("192.168.1.1" in inp for inp in inputs)
    assert any("example.com" in inp for inp in inputs)
    assert any("123-45-6789" in inp for inp in inputs)

