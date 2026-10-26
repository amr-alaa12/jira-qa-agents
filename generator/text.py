"""Small helpers that pull readable phrases out of stories and criteria."""

from __future__ import annotations

import re
from typing import Optional

_SUBJECT_RE = re.compile(
    r"^(?P<subject>.+?)\s+(?:must|should|shall|cannot|can't|can|will|may|has\s+to|have\s+to"
    r"|needs?\s+to|is|are|gets?|receives?|loads?|returns?|responds?|opens?|appears?|displays?|shows?)\b",
    re.IGNORECASE,
)
_STORY_ACTION_RE = re.compile(
    r"\bI\s+(?:want|would\s+like|need|wish)\s+to\s+(?P<action>.+?)(?:,?\s+so\s+that\b|[.;]|$)",
    re.IGNORECASE,
)
_CRITERION_ACTION_RE = re.compile(
    r"\b(?:can|may|is\s+allowed\s+to|are\s+allowed\s+to|is\s+able\s+to|are\s+able\s+to"
    r"|should\s+be\s+able\s+to|must\s+be\s+able\s+to)\s+(?P<action>.+)$",
    re.IGNORECASE,
)
_ARTICLE_RE = re.compile(r"^(?:the|a|an)\s+", re.IGNORECASE)
# Words that start with a vowel letter but a consonant sound, and the reverse.
_A_EXCEPTIONS = ("user", "uni", "use", "usa", "eu", "one", "once")
_AN_EXCEPTIONS = ("hour", "honest", "honor", "honour")


def sentence(value: str) -> str:
    """Collapse whitespace and drop the final full stop."""
    return re.sub(r"\s+", " ", value).strip().rstrip(".!;:").strip()


def capitalize(value: str) -> str:
    return value[:1].upper() + value[1:]


def lower_first(value: str) -> str:
    """Lower-case the first letter unless the first word is an acronym (URL, PIN)."""
    first_word = value.split(" ", 1)[0]
    if len(first_word) > 1 and first_word.isupper():
        return value
    return value[:1].lower() + value[1:]


def strip_article(value: str) -> str:
    return _ARTICLE_RE.sub("", value, count=1)


def article(noun: str) -> str:
    """Return "a" or "an" for a noun phrase."""
    lowered = noun.lower()
    if lowered.startswith(_AN_EXCEPTIONS):
        return "an"
    if lowered.startswith(_A_EXCEPTIONS):
        return "a"
    return "an" if lowered[:1] in "aeiou" else "a"


def with_article(noun: str) -> str:
    return f"{article(noun)} {noun}"


def subject(criterion: str) -> Optional[str]:
    """The thing a criterion talks about: "The new password must ..." -> "new password"."""
    match = _SUBJECT_RE.match(sentence(criterion))
    if not match:
        return None
    found = lower_first(strip_article(match["subject"].strip()))
    if not found or len(found.split()) > 5:
        return None
    return singular(found)


def singular(noun_phrase: str) -> str:
    """Make the last word singular so titles read "Password with ... is": "passwords" -> "password"."""
    words = noun_phrase.split(" ")
    last = words[-1]
    if len(last) > 3 and last.endswith("s") and not last.lower().endswith(("ss", "us", "is", "ous")):
        words[-1] = last[:-3] + "y" if last.lower().endswith("ies") else last[:-1]
    return " ".join(words)


def story_action(description: str) -> Optional[str]:
    """The user's goal: "I want to reset my password so that ..." -> "reset the password"."""
    match = _STORY_ACTION_RE.search(description or "")
    if not match:
        return None
    action = re.sub(r"\bmy\b", "the", match["action"].strip(), flags=re.IGNORECASE)
    return lower_first(sentence(action)) or None


def criterion_action(criterion: str) -> Optional[str]:
    """What a criterion allows: "Only admins can delete products" -> "delete products"."""
    match = _CRITERION_ACTION_RE.search(sentence(criterion))
    return match["action"].strip() if match else None
