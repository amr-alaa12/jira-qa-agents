from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Sequence

from . import text
from .templates import TEMPLATES, StoryContext
from .text import to_gherkin

CATEGORIES = (
    "functional",
    "validation",
    "boundary",
    "security",
    "performance",
    "usability",
    "reliability",
    "portability",
    "maintainability",
)
TEST_CASE_FIELDS = ("story_key", "id", "title", "type", "input", "steps", "expected")
OPTIONAL_FIELDS = ("priority", "preconditions", "execution_type", "gherkin")
ALL_FIELDS = TEST_CASE_FIELDS + OPTIONAL_FIELDS


def generate_test_cases(story: Mapping[str, Any],
                        categories: Sequence[Any],
                        include_optional: bool = False,
                        deduplicate: bool = False) -> List[Dict[str, Any]]:
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
            tc: Dict[str, Any] = {
                "story_key": context.key,
                "id": f"{context.key}-TC{len(test_cases) + 1}",
                "title": draft.title,
                "type": category,
                "input": draft.input,
                "steps": list(draft.steps),
                "expected": draft.expected,
            }
            if include_optional:
                is_negative = "rejected" in draft.title.lower() or "denied" in draft.title.lower()
                tc["priority"] = draft.priority or _default_priority(category, is_negative)
                tc["preconditions"] = list(draft.preconditions) if draft.preconditions else _default_preconditions(context, category, criterion)
                tc["execution_type"] = draft.execution_type or _default_execution_type(category)
                tc["gherkin"] = to_gherkin(tc)
            test_cases.append(tc)

    if deduplicate:
        return deduplicate_test_cases(test_cases)
    return test_cases


def generate_for_stories(stories: Iterable[Mapping[str, Any]],
                         categories_by_key: Mapping[str, Sequence[Any]],
                         include_optional: bool = False,
                         deduplicate: bool = False) -> List[Dict[str, Any]]:
    stories = list(stories)
    missing = [str(story.get("key")) for story in stories if story.get("key") not in categories_by_key]
    if missing:
        raise ValueError(f"No categories given for these stories: {', '.join(missing)}")
    test_cases: List[Dict[str, Any]] = []
    for story in stories:
        test_cases.extend(
            generate_test_cases(
                story,
                categories_by_key[story["key"]],
                include_optional=include_optional,
                deduplicate=deduplicate,
            )
        )
    return test_cases


def deduplicate_test_cases(test_cases: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    unique: List[Dict[str, Any]] = []
    for tc in test_cases:
        sig = (
            str(tc.get("story_key")),
            str(tc.get("type")),
            str(tc.get("input")),
            tuple(str(s) for s in (tc.get("steps") or [])),
            str(tc.get("expected")),
        )
        if sig in seen:
            continue
        seen.add(sig)
        unique.append(dict(tc))

    per_story_count: Dict[str, int] = {}
    for item in unique:
        sk = str(item["story_key"])
        per_story_count[sk] = per_story_count.get(sk, 0) + 1
        item["id"] = f"{sk}-TC{per_story_count[sk]}"
    return unique


def _default_priority(category: str, is_negative: bool) -> str:
    if category == "security":
        return "Critical"
    if category in ("validation", "boundary") and is_negative:
        return "High"
    if category in ("functional", "reliability"):
        return "High"
    if category in ("performance", "portability"):
        return "Medium"
    return "Low"


def _default_preconditions(context: StoryContext, category: str, criterion: str = "") -> List[str]:
    feature = context.feature_name
    extracted = text.extract_condition_precondition(criterion) if criterion else None
    if category == "security":
        base = ["User accounts with configured permission roles exist", f"{feature} service is online"]
    elif category == "performance":
        base = [f"{feature} is deployed in the test environment", "Load injection harness is operational"]
    elif category == "reliability":
        base = [f"{feature} is operational under standard baseline conditions", "Fault injection tools are ready"]
    elif category == "portability":
        base = [f"{feature} is deployed and accessible across target client environments"]
    elif category == "maintainability":
        base = [f"Source code repository and component boundaries for {feature} are available"]
    else:
        base = [f"User is on the {feature} page with active connectivity"]
    if extracted and extracted not in base:
        return [extracted] + base
    return base


def _default_execution_type(category: str) -> str:
    if category == "security":
        return "security"
    if category == "performance":
        return "load"
    if category in ("usability", "maintainability"):
        return "manual"
    return "automated"


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
