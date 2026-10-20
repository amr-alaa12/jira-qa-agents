"""Test Case Generator (Member 4).

    from generator import generate_test_cases
    test_cases = generate_test_cases(story, ["functional", "boundary"])
"""

from .core import CATEGORIES, TEST_CASE_FIELDS, generate_for_stories, generate_test_cases

__all__ = ["CATEGORIES", "TEST_CASE_FIELDS", "generate_for_stories", "generate_test_cases"]
