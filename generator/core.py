"""Turn a story and the category of each acceptance criterion into test cases."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Sequence

from .templates import TEMPLATES, StoryContext

CATEGORIES = ("functional", "validation", "boundary", "security", "performance", "usability")
TEST_CASE_FIELDS = ("story_key", "id", "title", "type", "input", "steps", "expected")


def generate_test_cases(story: Mapping[str, Any], categories: Sequence[Any]) -> List[Dict[str, Any]]:
    """Return the test cases for one story, in the agreed test case format.

    Each test case states its ``input`` (the test data) and its ``expected`` output.

    ``categories`` holds one category per acceptance criterion, in the same
    order. Each item is a category name ("boundary") or the
    ``(category, confidence)`` pair returned by ``predict_category``.
    Every criterion produces at least two test cases; ids run
    ``<key>-TC1``, ``<key>-TC2``, ... across the whole story.
    """
    criteria = _criteria(story)
    names = [_category_name(item) for item in categories]
    if len(names) != len(criteria):
        raise ValueError(
            f"Story {story['key']} has {len(criteria)} acceptance criteria "
            f"but {len(names)} categories were given; give exactly one category per criterion"
        )

    context = StoryContext.from_story(story)
    test_cases: List[Dict[str, Any]] = []
    for criterion, category in zip(criteria, names):
        for draft in TEMPLATES[category](context, criterion):
            test_cases.append({
                "story_key": context.key,
                "id": f"{context.key}-TC{len(test_cases) + 1}",
                "title": draft.title,
                "type": category,
                "input": draft.input,
                "steps": list(draft.steps),
                "expected": draft.expected,
            })
    return test_cases


def generate_for_stories(stories: Iterable[Mapping[str, Any]],
                         categories_by_key: Mapping[str, Sequence[Any]]) -> List[Dict[str, Any]]:
    """Generate test cases for many stories; ``categories_by_key`` maps story key -> categories."""
    stories = list(stories)
    missing = [str(story.get("key")) for story in stories if story.get("key") not in categories_by_key]
    if missing:
        raise ValueError(f"No categories given for these stories: {', '.join(missing)}")
    test_cases: List[Dict[str, Any]] = []
    for story in stories:
        test_cases.extend(generate_test_cases(story, categories_by_key[story["key"]]))
    return test_cases


def _criteria(story: Mapping[str, Any]) -> List[str]:
    if not isinstance(story, Mapping):
        raise ValueError("A story must be a JSON object")
    key = story.get("key")
    if not isinstance(key, str) or not key.strip():
        raise ValueError("A story needs a non-empty 'key', for example \"SHOP-1\"")
    criteria = story.get("acceptance_criteria", [])
    if not isinstance(criteria, list):
        raise ValueError(f"Story {key}: 'acceptance_criteria' must be a list of sentences")
    for number, criterion in enumerate(criteria, start=1):
        if not isinstance(criterion, str) or not criterion.strip():
            raise ValueError(f"Story {key}: acceptance criterion {number} is empty or not text")
    return [criterion.strip() for criterion in criteria]


def _category_name(item: Any) -> str:
    if isinstance(item, (tuple, list)) and item:
        item = item[0]
    if not isinstance(item, str):
        raise ValueError(f"Category {item!r} is not text; use one of: {', '.join(CATEGORIES)}")
    name = item.strip().lower()
    if name not in TEMPLATES:
        raise ValueError(f"Unknown category {item!r}; use one of: {', '.join(CATEGORIES)}")
    return name
