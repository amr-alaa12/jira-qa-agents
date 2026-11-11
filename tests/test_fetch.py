import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from jira.fetch import extract_criteria


def test_bold_text_stays_in_one_criterion():
    doc = {"type": "doc", "content": [
        {"type": "heading", "content": [{"type": "text", "text": "Acceptance Criteria"}]},
        {"type": "bulletList", "content": [
            {"type": "listItem", "content": [
                {"type": "paragraph", "content": [
                    {"type": "text", "text": "The password must be "},
                    {"type": "text", "text": "at least 8", "marks": [{"type": "strong"}]},
                    {"type": "text", "text": " characters"},
                ]},
            ]},
        ]},
    ]}
    assert extract_criteria(doc) == ["The password must be at least 8 characters"]


def paragraph_doc(*paragraphs):
    return {"type": "doc", "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": text}]} for text in paragraphs]}


def test_inline_numbered_criteria_in_the_description():
    """Real Jira story MOD-46: criteria written inside the description paragraph."""
    doc = paragraph_doc(
        "As a owner, I want a GitHub import screen, so that I can add new repos as projects. "
        "Acceptance Criteria: 1. Given the import screen, then new repos are listed and selectable. "
        "2. Given I confirm, then selected repos are imported and appear in Content.")
    assert extract_criteria(doc) == [
        "Given the import screen, then new repos are listed and selectable.",
        "Given I confirm, then selected repos are imported and appear in Content.",
    ]


def test_inline_marker_followed_by_lines():
    doc = paragraph_doc("Acceptance criteria:", "1) The user can log in", "2) The user can log out",
                        "Notes", "Not a criterion")
    assert extract_criteria(doc) == ["The user can log in", "The user can log out"]


def test_heading_style_still_works():
    doc = {"type": "doc", "content": [
        {"type": "heading", "content": [{"type": "text", "text": "Acceptance Criteria"}]},
        {"type": "bulletList", "content": [
            {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "A"}]}]},
            {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "B"}]}]},
        ]},
    ]}
    assert extract_criteria(doc) == ["A", "B"]


def test_a_single_number_is_not_split():
    doc = paragraph_doc("Acceptance Criteria: The page loads within 2. seconds on version 3. of the app")
    assert extract_criteria(doc) == ["The page loads within 2. seconds on version 3. of the app"]


def test_no_marker_means_no_criteria():
    assert extract_criteria(paragraph_doc("As a user I want things. 1. one 2. two")) == []
