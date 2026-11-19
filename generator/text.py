from __future__ import annotations

import re
from typing import Any, Mapping, Optional

_SUBJECT_RE = re.compile(
    r"^(?P<subject>.+?)\s+(?:must|should|shall|cannot|can't|can|will|may|has\s+to|have\s+to"
    r"|needs?\s+to|is|are|gets?|receives?|loads?|returns?|responds?|opens?|appears?|displays?|shows?)\b",
    re.IGNORECASE,
)
_STORY_ACTION_RE = re.compile(
    r"\bI\s+(?:want|would\s+like|need|wish)\s+to\s+(?P<action>.+?)(?:,?\s+so\s+that\b|[.;]|$)",
    re.IGNORECASE,
)
_STORY_PERSONA_RE = re.compile(
    r"\bAs\s+(?:an?|the)\s+(?P<role>[^,]+?),\s*I\s+(?:want|would\s+like|need|wish)\b",
    re.IGNORECASE,
)
_STORY_BENEFIT_RE = re.compile(
    r"\bso\s+that\s+(?P<benefit>[^.;!]+)",
    re.IGNORECASE,
)
_CRITERION_ACTION_RE = re.compile(
    r"\b(?:can|may|is\s+allowed\s+to|are\s+allowed\s+to|is\s+able\s+to|are\s+able\s+to"
    r"|should\s+be\s+able\s+to|must\s+be\s+able\s+to)\s+(?P<action>.+)$",
    re.IGNORECASE,
)
_ARTICLE_RE = re.compile(r"^(?:the|a|an)\s+", re.IGNORECASE)
_A_EXCEPTIONS = ("user", "uni", "use", "usa", "eu", "one", "once")
_AN_EXCEPTIONS = ("hour", "honest", "honor", "honour")
_PAGE_SUFFIXES = ("page", "modal", "screen", "view", "dialog", "dashboard", "tab", "portal", "window", "panel")


def sentence(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().rstrip(".!;:").strip()


def capitalize(value: str) -> str:
    return value[:1].upper() + value[1:]


def lower_first(value: str) -> str:
    first_word = value.split(" ", 1)[0]
    if len(first_word) > 1 and first_word.isupper():
        return value
    return value[:1].lower() + value[1:]


def strip_article(value: str) -> str:
    return _ARTICLE_RE.sub("", value, count=1)


def article(noun: str) -> str:
    lowered = noun.lower()
    if lowered.startswith(_AN_EXCEPTIONS):
        return "an"
    if lowered.startswith(_A_EXCEPTIONS):
        return "a"
    return "an" if lowered[:1] in "aeiou" else "a"


def with_article(noun: str) -> str:
    return f"{article(noun)} {noun}"


def subject(criterion: str) -> Optional[str]:
    match = _SUBJECT_RE.match(sentence(criterion))
    if not match:
        return None
    found = lower_first(strip_article(match["subject"].strip()))
    if not found or len(found.split()) > 5:
        return None
    return singular(found)


def singular(noun_phrase: str) -> str:
    words = noun_phrase.split(" ")
    last = words[-1]
    if len(last) > 3 and last.endswith("s") and not last.lower().endswith(("ss", "us", "is", "ous")):
        words[-1] = last[:-3] + "y" if last.lower().endswith("ies") else last[:-1]
    return " ".join(words)


def story_action(description: str) -> Optional[str]:
    match = _STORY_ACTION_RE.search(description or "")
    if not match:
        return None
    action = re.sub(r"\bmy\b", "the", match["action"].strip(), flags=re.IGNORECASE)
    return lower_first(sentence(action)) or None


def story_persona(description: str) -> Optional[str]:
    match = _STORY_PERSONA_RE.search(description or "")
    if not match:
        return None
    return lower_first(sentence(match["role"].strip())) or None


def story_benefit(description: str) -> Optional[str]:
    match = _STORY_BENEFIT_RE.search(description or "")
    if not match:
        return None
    benefit = re.sub(r"\bmy\b", "the", match["benefit"].strip(), flags=re.IGNORECASE)
    return lower_first(sentence(benefit)) or None


def clean_page_name(feature: str) -> str:
    cleaned = sentence(feature).lower()
    if any(cleaned.endswith(suffix) for suffix in _PAGE_SUFFIXES):
        return feature
    return f"{feature} page"


def action_button(phrase: str) -> str:
    lowered = phrase.lower()
    if re.search(r"\b(?:reset\s+password|password\s+reset)\b", lowered):
        return "Submit the form"
    if re.search(r"\b(?:checkout|pay|payment|place\s+order)\b", lowered):
        return "Click Place Order"
    if re.search(r"\b(?:log\s*in|sign\s*in)\b", lowered):
        return "Click Log In"
    if re.search(r"\b(?:register|sign\s*up)\b", lowered):
        return "Click Register"
    if re.search(r"\b(?:search|find|query)\b", lowered):
        return "Click Search"
    if re.search(r"\b(?:delete|remove)\b", lowered):
        return "Click Delete and confirm"
    if re.search(r"\b(?:save|update|edit)\b", lowered):
        return "Click Save"
    if re.search(r"\b(?:add|create)\b", lowered):
        return "Click Add"
    if re.search(r"\b(?:export|download)\b", lowered):
        return "Click Export"
    return "Submit the form"


def criterion_action(criterion: str) -> Optional[str]:
    match = _CRITERION_ACTION_RE.search(sentence(criterion))
    return match["action"].strip() if match else None


def to_gherkin(test_case: Mapping[str, Any]) -> str:
    title = str(test_case.get("title") or "Scenario")
    steps = [str(s) for s in (test_case.get("steps") or [])]
    expected = str(test_case.get("expected") or "The expected result is verified")
    lines = [f"Scenario: {title}"]
    if steps:
        lines.append(f"  Given {capitalize(steps[0])}")
        if len(steps) > 1:
            lines.append(f"  When {capitalize(steps[1])}")
            for step in steps[2:]:
                lines.append(f"  And {capitalize(step)}")
    lines.append(f"  Then {capitalize(expected)}")
    return "\n".join(lines)
