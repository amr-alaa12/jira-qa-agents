"""Negative test cases must assert the opposite of the criterion's outcome, never the outcome itself."""

import pytest

from generator import generate_test_cases, text

REVIEW = {
    "key": "KAN-9",
    "title": "Product review",
    "description": "As a customer, I want to review a product so that other shoppers can read it.",
    "acceptance_criteria": [
        "Given I have bought the product, when I submit a review, then the review should be saved successfully",
    ],
}


@pytest.mark.parametrize("statement, negated", [
    ("the review should be saved successfully", "the review is not saved"),
    ("The user receives a reset link by email", "The user does not receive a reset link by email"),
    ("the system should create the order and display the order summary",
     "the system does not create the order or display the order summary"),
    ("the page is shown", "the page is not shown"),
    ("users can see their orders", "users cannot see their orders"),
    ("Search results must match the entered product name", "Search results do not match the entered product name"),
    ("The status update appears on the page", "The status update does not appear on the page"),
])
def test_negate_states_the_logical_opposite(statement, negated):
    assert text.negate(statement) == negated


@pytest.mark.parametrize("statement", [
    "the password must not be stored in plain text",   # already negative
    "Orders over $50 get free shipping",              # no safe subject/verb split
])
def test_negate_refuses_what_it_cannot_state_safely(statement):
    assert text.negate(statement) is None


@pytest.mark.parametrize("statement, affirmed", [
    ("the review should be saved successfully", "the review is saved successfully"),
    ("the system should create the order and display the order summary",
     "the system creates the order and displays the order summary"),
    ("I should receive an email", "I receive an email"),
    ("The user receives a reset link by email", "The user receives a reset link by email"),
])
def test_affirm_turns_a_requirement_into_an_observation(statement, affirmed):
    assert text.affirm(statement) == affirmed


def test_negative_cases_never_contain_the_positive_outcome():
    cases = generate_test_cases(REVIEW, ["functional"])
    assert cases[0]["expected_output"] == "A confirmation message is shown and the review is saved successfully"
    assert cases[1]["expected_output"] == (
        "The action is not completed, a validation error is shown next to the wrong field, "
        "and the review is not saved")
    assert cases[2]["expected_output"].endswith("and the review is not saved")
    for case in cases[1:]:
        assert "does not happen" not in case["expected_output"]
        assert "should be saved" not in case["expected_output"]


def test_field_negative_cases_negate_the_outcome():
    story = dict(REVIEW, title="Reset password", acceptance_criteria=["The user receives a reset link by email"])
    cases = generate_test_cases(story, ["functional"])
    assert cases[1]["expected_output"] == (
        "The email address is rejected, a validation error is shown next to the field, "
        "and the user does not receive a reset link by email")


def test_error_path_outcome_is_not_negated_into_a_success():
    story = dict(REVIEW, acceptance_criteria=[
        "Given the payment information is invalid, when I confirm the order, "
        "then the system should reject the payment and display an error message"])
    cases = generate_test_cases(story, ["functional"])
    assert cases[0]["expected_output"] == "The system rejects the payment and displays an error message"
    assert "confirmation message" not in cases[0]["expected_output"]
    assert cases[1]["expected_output"] == (
        "The action is not completed and a validation error is shown next to the wrong field")


def test_given_clause_becomes_a_setup_step():
    cases = generate_test_cases(REVIEW, ["functional"])
    assert all(case["steps"][1] == "Make sure that the user has bought the product" for case in cases)


def test_unnegatable_outcome_is_quoted_not_contradicted():
    story = dict(REVIEW, acceptance_criteria=["Orders over $50 get free shipping"])
    negative = generate_test_cases(story, ["functional"])[1]["expected_output"]
    assert negative.endswith('the expected result ("orders over $50 get free shipping") does not occur')


OPT_OUT = {
    "key": "MOD-42",
    "title": "Respect STOP and unsubscribe requests",
    "description": "As a customer, I want to opt out by replying STOP so that I stop receiving messages.",
    "acceptance_criteria": ["Given I have opted out, when a campaign is sent, then no automatic reply is sent to me"],
}


@pytest.mark.parametrize("statement", [
    "no automatic reply is sent to me",
    "nothing is charged",
    "none of the items are removed",
])
def test_already_negative_outcomes_are_not_negated_again(statement):
    assert text.negate(statement) is None
    assert text.is_failure_outcome(statement)


def test_negative_outcome_never_becomes_a_double_negative():
    cases = generate_test_cases(OPT_OUT, ["functional"])
    assert cases[0]["expected_output"] == "No automatic reply is sent to the user"
    assert cases[2]["expected_output"] == (
        "The action is not completed and a required-field message is shown for each empty field")
    for case in cases:
        assert " no " not in case["expected_output"].lower().replace("no automatic", "")
        assert "is not sent" not in case["expected_output"]


@pytest.mark.parametrize("statement, rewritten", [
    ("no automatic reply is sent to me", "no automatic reply is sent to the user"),
    ("I receive an email", "the user receives an email"),
    ("I should receive my receipt", "the user should receive the receipt"),
])
def test_first_person_outcomes_are_written_about_the_user(statement, rewritten):
    assert text.about_user(statement) == rewritten


# --- audit of 11 Nov 2026: defects found by running ~3,200 generated cases ---------------

def _cases(criterion, category, title="Profile", description=""):
    story = {"key": "T-1", "title": title, "description": description, "acceptance_criteria": [criterion]}
    return generate_test_cases(story, [category])


def test_negated_limit_is_turned_around():
    """'cannot be longer than 12' allows 12 and rejects 13 (it used to accept 13)."""
    cases = _cases("The display name cannot be longer than 12 characters", "boundary")
    assert [c["title"] for c in cases] == [
        "Display name with 11 characters is accepted",
        "Display name with 12 characters is accepted",
        "Display name with 13 characters is rejected",
    ]
    assert "(at most 12 characters)" in cases[2]["expected_output"]


def test_subject_is_not_cut_at_a_noun_that_looks_like_a_verb():
    assert text.subject("The display name cannot be longer than 12 characters") == "display name"
    assert text.subject("The display page shows the total") == "display page"


def test_subject_drops_a_trailing_preposition():
    assert _cases("A comment with exactly 4 characters is accepted", "boundary")[0]["title"].startswith(
        "Comment with 3 characters")


def test_limit_on_a_persons_action_reads_allowed_or_refused():
    cases = _cases("Customers can cancel an order within 24 hours", "boundary")
    assert cases[0]["title"] == "Cancel an order after 23 hours: allowed"
    assert cases[2]["expected_output"].startswith("The customer cannot cancel an order after 25 hours")
    sessions = _cases("A user cannot have more than 5 active sessions", "boundary")
    assert sessions[2]["title"] == "Have 6 active sessions: refused"


def test_given_when_then_is_not_quoted_into_other_templates():
    criterion = "Given I have bought the product, when I submit a review, then the review should be saved"
    for category in ("boundary", "performance", "usability"):
        for case in _cases(criterion, category):
            assert "given" not in case["expected_output"].lower()
            assert " I " not in f" {case['expected_output']} "


def test_leading_clause_is_kept_as_context_when_negating():
    assert text.negate("After the user clicks Save, a confirmation email is sent to the user") == (
        "a confirmation email is not sent to the user after the user clicks Save")


def test_permissions_and_only_rules_are_not_negated():
    for criterion in ("Customers can edit their review within 24 hours", "Only admins can re-subscribe a customer"):
        negative = _cases(criterion, "functional")[1]["expected_output"]
        assert negative == "The action is not completed and a validation error is shown next to the wrong field"


def test_page_name_comes_from_the_noun_of_a_verb_title():
    steps = _cases("The reply is logged", "functional", title="Respect STOP and unsubscribe requests")[0]["steps"]
    assert steps[0] == "Open the STOP and unsubscribe requests page"
    assert _cases("x is shown", "functional", title="Place an order using the cart")[0]["steps"][0] == (
        "Open the order page")


def test_validation_field_is_not_an_actor():
    criterion = ("Given the payment information is invalid, when I confirm the order, "
                 "then the system should reject the payment")
    assert _cases(criterion, "validation")[0]["title"] == "Valid payment information is accepted"


def test_email_notification_is_not_an_email_field():
    first = _cases("An email notification is sent when an account is deactivated", "functional")[0]
    assert "email address" not in first["input"].lower()


def test_security_compares_the_named_group():
    cases = _cases("Deactivated users cannot log in", "security")
    assert [c["title"] for c in cases] == ["User who is not deactivated can log in", "Deactivated user cannot log in"]
    without = _cases("Users without permission cannot access the admin dashboard", "security")
    assert without[0]["title"] == "User with permission can access the admin dashboard"


def test_security_for_other_users_data():
    cases = _cases("Users cannot delete other users' orders", "security")
    assert cases[0]["title"] == "User can delete their own orders"
    assert cases[1]["title"] == "User cannot delete other users' orders"


def test_data_protection_checks_storage_not_logins():
    cases = _cases("Passwords are stored hashed", "security")
    assert cases[0]["title"] == "Password is never stored in plain text"
    assert all("Log in" not in step for case in cases for step in case["steps"])


def test_security_group_ignores_the_article_and_guests_are_anonymous():
    steps = _cases("Only a manager can edit system settings", "security")[0]["steps"]
    assert steps[0] == "Log in as a user in the 'manager' group (manager.member@example.com)"
    assert _cases("Guests cannot see the order history", "security")[1]["steps"][0] == "Make sure no user is logged in"


def test_performance_title_agrees_with_a_plural_subject():
    assert _cases("Replies of STOP are processed within 5 minutes", "performance")[0]["title"].startswith(
        "Replies of STOP meet the target")


def test_first_person_is_rewritten_everywhere():
    assert text.about_user("When I reply STOP, I should not receive messages") == (
        "When the user replies STOP, the user should not receive messages")
    assert text.precondition("Given I am on the login page, when I log in, then I see my orders") == (
        "the user is on the login page")


# --- live-site review (SHOP-2, SHOP-3): shapes the category templates got wrong ---------

from generator.core import generate_test_cases  # noqa: E402


def _shaped_cases(title, description, criterion, category):
    story = {"key": "T", "title": title, "description": description, "acceptance_criteria": [criterion]}
    return generate_test_cases(story, [category])


def test_incorrect_password_is_a_wrong_password_not_a_weak_one():
    for category in ("validation", "functional", "security"):
        cases = _shaped_cases("User login", "As a user, I want to log in.", "Incorrect passwords must be rejected", category)
        titles = " ".join(case["title"] for case in cases).lower()
        assert "weak" not in titles and "spaces only" not in titles
        assert any("incorrect password for a registered account" in case["title"].lower() for case in cases)
        assert all(case["type"] == category for case in cases)


def test_only_authenticated_users_is_a_login_state_not_a_group():
    cases = _shaped_cases("User login", "As a user, I want to log in.",
                   "Only authenticated users can access their account", "security")
    assert "group" not in " ".join(case["title"] for case in cases)
    assert cases[0]["title"].startswith("Logged-in user can")
    assert "not logged in" in cases[1]["title"]


def test_empty_search_tests_empty_blank_and_real_text():
    cases = _shaped_cases("Product search", "As a customer, I want to search for products by name.",
                   "An empty search must show a helpful message", "validation")
    titles = [case["title"] for case in cases]
    assert titles[0] == "Empty search shows a helpful message"
    assert "spaces only" in titles[1]
    assert not any("valid empty" in title.lower() or "wrong format" in title for title in titles)
    assert cases[0]["expected_output"].startswith("A helpful message is shown")


def test_results_must_match_input_tests_the_results():
    for category in ("validation", "functional"):
        cases = _shaped_cases("Product search", "As a customer, I want to search for products by name.",
                       "Search results must match the entered product name", category)
        assert "forbidden characters" not in " ".join(case["title"] for case in cases)
        assert "matches nothing returns no results" in cases[1]["title"]


def test_shapes_do_not_touch_other_categories():
    cases = _shaped_cases("Product search", "As a customer, I want to search.",
                   "An empty search must show a helpful message within 1 second", "performance")
    assert not any("spaces only" in case["title"] for case in cases)
