from decimal import Decimal

import pytest

from generator.limits import (EXACT, MAX, MAX_EXCLUSIVE, MIN, MIN_EXCLUSIVE, RANGE, TRIGGER,
                              extract_limits)


def probe_values(limit):
    return [(str(value), inside) for value, inside in limit.probes()]


def only_limit(criterion):
    limits = extract_limits(criterion)
    assert len(limits) == 1, limits
    return limits[0]


def test_at_least_probes_just_below_at_and_just_above():
    limit = only_limit("The new password must be at least 8 characters")
    assert limit.relation == MIN
    assert limit.unit == "characters"
    assert limit.kind == "length"
    assert limit.phrase == "at least 8 characters"
    assert probe_values(limit) == [("7", False), ("8", True), ("9", True)]


@pytest.mark.parametrize("criterion, relation, inside", [
    ("The cart can hold at most 10 items", MAX, [True, True, False]),
    ("Passwords must not exceed 64 characters", MAX, [True, True, False]),
    ("The bio can be up to 200 characters", MAX, [True, True, False]),
    ("Orders over $50 get free shipping", MIN_EXCLUSIVE, [False, False, True]),
    ("The page loads in under 2 seconds", MAX_EXCLUSIVE, [True, False, False]),
    ("The PIN must be exactly 4 digits", EXACT, [False, True, False]),
    ("The account is locked after 3 failed login attempts", TRIGGER, [False, True, True]),
    ("The code must be 8 or more characters", MIN, [False, True, True]),
])
def test_relation_is_read_from_the_wording(criterion, relation, inside):
    limit = only_limit(criterion)
    assert limit.relation == relation
    assert [ok for _, ok in limit.probes()] == inside


def test_range_probes_both_ends():
    limit = only_limit("The username must be between 3 and 20 characters")
    assert limit.relation == RANGE
    assert probe_values(limit) == [("2", False), ("3", True), ("20", True), ("21", False)]


def test_money_uses_cent_steps_and_keeps_the_currency():
    limit = only_limit("Orders over $50 get free shipping")
    assert [limit.format(value) for value, _ in limit.probes()] == ["$49.99", "$50", "$50.01"]
    assert limit.phrase == "over $50"


def test_decimal_numbers_use_decimal_steps():
    limit = only_limit("Search results appear within 1.5 seconds")
    assert limit.relation == MAX
    assert [str(value) for value, _ in limit.probes()] == ["1.4", "1.5", "1.6"]


def test_number_words_are_understood():
    limit = only_limit("The cart must contain at least one item")
    assert limit.low == Decimal(1)
    assert limit.format(Decimal(1)) == "1 item"
    assert limit.format(Decimal(2)) == "2 items"


def test_unit_can_span_several_words():
    limit = only_limit("The account is locked after 3 failed login attempts")
    assert limit.unit == "failed login attempts"
    assert limit.format(Decimal(1)) == "1 failed login attempt"


def test_time_without_qualifier_is_read_as_a_deadline():
    limit = only_limit("The report is generated in 5 seconds")
    assert limit.relation == MAX
    assert limit.phrase == "within 5 seconds"


def test_several_limits_in_one_criterion():
    limits = extract_limits("The password must be at least 8 characters and at most 64 characters")
    assert [(limit.relation, limit.low) for limit in limits] == [(MIN, 8), (MAX, 64)]


def test_negative_values_are_not_probed_for_zero_limits():
    limit = only_limit("The cart can have at least 0 items")
    assert [str(value) for value, _ in limit.probes()] == ["0", "1"]


def test_percent_and_plain_numbers():
    assert only_limit("Battery use must stay below 80%").format(Decimal(79)) == "79%"
    assert only_limit("The PIN must be exactly 4 digits").relation == EXACT


def test_text_without_numbers_has_no_limits():
    assert extract_limits("The user receives a reset link by email") == []
