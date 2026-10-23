import json
from pathlib import Path

import pytest

from generator import CATEGORIES, TEST_CASE_FIELDS, generate_for_stories, generate_test_cases

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"

RESET_PASSWORD = {
    "key": "SHOP-1",
    "title": "Reset password",
    "description": "As a user, I want to reset my password so that I can log in again.",
    "acceptance_criteria": [
        "The user receives a reset link by email",
        "The new password must be at least 8 characters",
    ],
}
LOGIN = {
    "key": "SHOP-2",
    "title": "Log in",
    "description": "As a customer, I want to log in to my account so that I can see my orders.",
    "acceptance_criteria": [
        "The email address must be valid",
        "The account is locked after 3 failed login attempts",
        "Only logged-in users can see the order history",
        "The login page loads in under 2 seconds",
    ],
}
PRODUCT_ADMIN = {
    "key": "SHOP-3",
    "title": "Manage products",
    "description": "As a store administrator, I want to manage products so that the catalog stays correct.",
    "acceptance_criteria": [
        "Only admins can delete products",
        "The product name must be between 3 and 50 characters",
        "Error messages explain what went wrong",
    ],
}
CHECKOUT = {
    "key": "SHOP-4",
    "title": "Checkout",
    "description": "As a shopper, I want to pay for my order so that it ships to me.",
    "acceptance_criteria": [
        "Orders over $50 get free shipping",
        "The card number is required",
        "The checkout works on mobile phones",
        "The order confirmation is sent by email",
    ],
}
STORIES = {
    "SHOP-1": (RESET_PASSWORD, ["functional", "boundary"]),
    "SHOP-2": (LOGIN, ["validation", "boundary", "security", "performance"]),
    "SHOP-3": (PRODUCT_ADMIN, ["security", "boundary", "usability"]),
    "SHOP-4": (CHECKOUT, ["boundary", "validation", "usability", "functional"]),
}


def assert_agreed_format(test_case):
    """The format agreed at kickoff (examples/test_cases.json)."""
    assert tuple(test_case) == TEST_CASE_FIELDS
    for field in ("story_key", "id", "title", "type", "input", "expected"):
        assert isinstance(test_case[field], str) and test_case[field].strip(), field
    assert test_case["type"] in CATEGORIES
    assert isinstance(test_case["steps"], list) and test_case["steps"]
    assert all(isinstance(step, str) and step.strip() for step in test_case["steps"])


def test_output_matches_the_shared_example_format():
    example = json.loads((EXAMPLES / "test_cases.json").read_text(encoding="utf-8"))[0]
    story = json.loads((EXAMPLES / "stories.json").read_text(encoding="utf-8"))[0]
    test_cases = generate_test_cases(story, ["functional", "boundary"])
    for test_case in test_cases:
        assert set(example) <= set(test_case)  # plus "input", agreed on 21/10
        assert_agreed_format(test_case)


@pytest.mark.parametrize("key", sorted(STORIES))
def test_every_story_gets_valid_test_cases(key):
    story, categories = STORIES[key]
    test_cases = generate_test_cases(story, categories)

    for test_case in test_cases:
        assert_agreed_format(test_case)
        assert test_case["story_key"] == key
    assert [tc["id"] for tc in test_cases] == [f"{key}-TC{n}" for n in range(1, len(test_cases) + 1)]
    assert {tc["type"] for tc in test_cases} == set(categories)


@pytest.mark.parametrize("key", sorted(STORIES))
def test_at_least_two_test_cases_per_criterion(key):
    story, categories = STORIES[key]
    for criterion, category in zip(story["acceptance_criteria"], categories):
        one_criterion = dict(story, acceptance_criteria=[criterion])
        assert len(generate_test_cases(one_criterion, [category])) >= 2, criterion


@pytest.mark.parametrize("category", CATEGORIES)
@pytest.mark.parametrize("criterion", [
    "The user receives a reset link by email",
    "The new password must be at least 8 characters",
    "The page loads in under 2 seconds",
    "Only admins can delete products",
    "The form is easy to use",
])
def test_every_category_handles_any_criterion(category, criterion):
    story = dict(RESET_PASSWORD, acceptance_criteria=[criterion])
    test_cases = generate_test_cases(story, [category])
    assert len(test_cases) >= 2
    for test_case in test_cases:
        assert_agreed_format(test_case)
        assert test_case["type"] == category


def test_boundary_uses_the_number_in_the_criterion():
    test_cases = generate_test_cases(RESET_PASSWORD, ["functional", "boundary"])
    boundary = [tc for tc in test_cases if tc["type"] == "boundary"]
    assert [tc["title"] for tc in boundary] == [
        "New password with 7 characters is rejected",
        "New password with 8 characters is accepted",
        "New password with 9 characters is accepted",
    ]
    assert boundary[0]["steps"] == [
        "Open the reset password page",
        'Enter "Passw0r" (7 characters) in the new password field',
        "Submit the form",
    ]
    assert "rejected" in boundary[0]["expected"] and "at least 8 characters" in boundary[0]["expected"]
    assert "form is submitted" in boundary[1]["expected"]
    assert [tc["input"] for tc in boundary] == [
        'New password: "Passw0r" (7 characters)',
        'New password: "Passw0rd" (8 characters)',
        'New password: "Passw0rd!" (9 characters)',
    ]


def test_boundary_sample_has_exactly_the_tested_length():
    story = dict(PRODUCT_ADMIN, acceptance_criteria=[PRODUCT_ADMIN["acceptance_criteria"][1]])
    inputs = [tc["input"] for tc in generate_test_cases(story, ["boundary"])]
    assert inputs[0] == 'Product name: "ab" (2 characters)'
    assert inputs[3] == 'Product name: "a" repeated 51 times (51 characters)'


def test_boundary_input_for_attempts_is_the_count():
    story = dict(LOGIN, acceptance_criteria=["The account is locked after 3 failed login attempts"])
    inputs = [tc["input"] for tc in generate_test_cases(story, ["boundary"])]
    assert inputs == ["2 failed login attempts", "3 failed login attempts", "4 failed login attempts"]


def test_boundary_range_tests_both_ends():
    story = dict(PRODUCT_ADMIN, acceptance_criteria=[PRODUCT_ADMIN["acceptance_criteria"][1]])
    titles = [tc["title"] for tc in generate_test_cases(story, ["boundary"])]
    assert titles == [
        "Product name with 2 characters is rejected",
        "Product name with 3 characters is accepted",
        "Product name with 50 characters is accepted",
        "Product name with 51 characters is rejected",
    ]


def test_boundary_without_a_number_still_gives_two_cases():
    story = dict(RESET_PASSWORD, acceptance_criteria=["The upload size is limited"])
    assert len(generate_test_cases(story, ["boundary"])) == 2


def test_validation_has_one_valid_and_two_invalid_inputs():
    story = dict(LOGIN, acceptance_criteria=["The email address must be valid"])
    test_cases = generate_test_cases(story, ["validation"])
    assert [tc["title"] for tc in test_cases] == [
        "Valid email address is accepted",
        "Email address without an @ sign is rejected",
        "Email address without a domain is rejected",
    ]
    assert [tc["input"] for tc in test_cases] == [
        'Email address: "user@example.com"',
        'Email address: "userexample.com"',
        'Email address: "user@"',
    ]


def test_required_field_is_tested_empty():
    story = dict(CHECKOUT, acceptance_criteria=["The card number is required"])
    test_cases = generate_test_cases(story, ["validation"])
    assert "Leave the card number field empty" in [tc["steps"][1] for tc in test_cases]
    assert "Card number: (empty)" in [tc["input"] for tc in test_cases]


def test_security_has_an_allowed_and_a_blocked_user():
    story = dict(PRODUCT_ADMIN, acceptance_criteria=["Only admins can delete products"])
    test_cases = generate_test_cases(story, ["security"])
    assert [tc["title"] for tc in test_cases] == [
        "Administrator can delete products",
        "Regular user (not an administrator) cannot delete products",
    ]
    assert "denied" in test_cases[1]["expected"]
    assert test_cases[0]["input"] == "User: administrator (admin@example.com)"
    assert test_cases[1]["steps"][0] == "Log in as a regular user (not an administrator) (user@example.com)"


def test_security_for_logged_in_users_uses_an_anonymous_visitor():
    story = dict(LOGIN, acceptance_criteria=["Only logged-in users can see the order history"])
    blocked = generate_test_cases(story, ["security"])[1]
    assert blocked["steps"][0] == "Make sure no user is logged in"


def test_functional_uses_concrete_values():
    test_cases = generate_test_cases(RESET_PASSWORD, ["functional", "boundary"])[:3]
    assert [tc["input"] for tc in test_cases] == [
        'Email address: "registered.user@example.com"',
        'Email address: "userexample.com"',
        'Email address: "" (empty)',
    ]
    assert test_cases[0]["steps"][1] == 'Enter the registered email address "registered.user@example.com"'
    assert test_cases[0]["expected"] == "A confirmation message is shown and the user receives a reset link by email"
    assert "validation error" in test_cases[1]["expected"]
    assert "required-field message" in test_cases[2]["expected"]


def test_functional_without_a_known_field_splits_wrong_and_empty():
    story = dict(PRODUCT_ADMIN, acceptance_criteria=["The product appears in the catalog"])
    inputs = [tc["input"] for tc in generate_test_cases(story, ["functional"])]
    assert inputs == [
        "All required fields: filled with correct values",
        "One required field: a value in the wrong format, the other fields correct",
        "All required fields: (empty)",
    ]


def test_performance_uses_the_time_limit():
    story = dict(LOGIN, acceptance_criteria=["The login page loads in under 2 seconds"])
    test_cases = generate_test_cases(story, ["performance"])
    assert test_cases[0]["expected"] == "Every measurement is under 2 seconds"
    assert "100 concurrent users" in test_cases[1]["title"]


def test_categories_may_come_straight_from_predict_category():
    from_model = [("functional", 0.88), ("BOUNDARY ", 0.91)]
    by_hand = ["functional", "boundary"]
    assert generate_test_cases(RESET_PASSWORD, from_model) == generate_test_cases(RESET_PASSWORD, by_hand)


def test_output_is_json_serializable_and_deterministic():
    first = generate_test_cases(LOGIN, STORIES["SHOP-2"][1])
    assert json.loads(json.dumps(first)) == first
    assert generate_test_cases(LOGIN, STORIES["SHOP-2"][1]) == first


def test_story_without_criteria_gives_no_test_cases():
    assert generate_test_cases(dict(RESET_PASSWORD, acceptance_criteria=[]), []) == []


@pytest.mark.parametrize("story, categories, message", [
    (RESET_PASSWORD, ["functional"], "2 acceptance criteria but 1 categories"),
    (RESET_PASSWORD, ["functional", "speed"], "Unknown category 'speed'"),
    (RESET_PASSWORD, ["functional", None], "is not text"),
    (dict(RESET_PASSWORD, key=""), ["functional", "boundary"], "non-empty 'key'"),
    (dict(RESET_PASSWORD, acceptance_criteria="one"), ["functional"], "must be a list"),
    (dict(RESET_PASSWORD, acceptance_criteria=["ok", "  "]), ["functional", "boundary"], "criterion 2 is empty"),
])
def test_bad_input_gives_a_clear_error(story, categories, message):
    with pytest.raises(ValueError, match=message):
        generate_test_cases(story, categories)


def test_generate_for_stories_numbers_each_story_separately():
    stories = [RESET_PASSWORD, LOGIN]
    test_cases = generate_for_stories(stories, {key: STORIES[key][1] for key in ("SHOP-1", "SHOP-2")})
    assert test_cases[0]["id"] == "SHOP-1-TC1"
    assert next(tc for tc in test_cases if tc["story_key"] == "SHOP-2")["id"] == "SHOP-2-TC1"


def test_generate_for_stories_names_stories_without_categories():
    with pytest.raises(ValueError, match="SHOP-2"):
        generate_for_stories([RESET_PASSWORD, LOGIN], {"SHOP-1": ["functional", "boundary"]})
