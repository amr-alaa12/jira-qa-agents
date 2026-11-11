"""Regression tests for the code-review fixes Z3-Z6."""
from generator import generate_test_cases
from generator.text import outcome


def story(*criteria, title="Checkout", description=""):
    return {"key": "T-1", "title": title, "description": description, "acceptance_criteria": list(criteria)}


def test_card_is_matched_as_a_whole_word_only():  # Z3
    cases = generate_test_cases(story("The dashboard shows the discard button"), ["validation"])
    assert not any("card number" in case["title"].lower() for case in cases)


def test_card_number_is_still_found():  # Z3
    cases = generate_test_cases(story("The card number is required"), ["validation"])
    assert cases[0]["title"] == "Valid card number is accepted"


def test_phone_is_matched_as_a_whole_word_only():  # Z3
    cases = generate_test_cases(story("The headphones page lists every model"), ["validation"])
    assert not any("phone number" in case["title"].lower() for case in cases)


def test_title_written_as_a_user_story_is_not_used_as_a_page_name():  # Z4
    cases = generate_test_cases(story("The email address must be valid", title="As a user I want to log in"),
                                ["validation"])
    assert all(case["steps"][0] == "Open the application" for case in cases)


def test_given_when_then_keeps_only_the_outcome():  # Z5
    criterion = "Given a registered user, when they enter a valid email, then the dashboard is shown"
    assert outcome(criterion) == "the dashboard is shown"
    assert outcome("The user receives a reset link by email.") == "The user receives a reset link by email"
    cases = generate_test_cases(story(criterion), ["functional"])
    assert cases[0]["title"] == "Registered email address: dashboard is shown"


def test_accepted_counts_as_a_rule_not_a_condition():  # Z6
    cases = generate_test_cases(story("Uploads between 1 and 5 files are accepted"), ["boundary"])
    titles = [case["title"] for case in cases]
    assert titles[0].endswith("0 files is rejected") and titles[-1].endswith("6 files is rejected")
