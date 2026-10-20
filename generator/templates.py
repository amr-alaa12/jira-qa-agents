"""One test-case template per requirement category.

Each template takes the story context and one acceptance criterion and
returns at least two drafts. The core module turns drafts into test cases
in the agreed format (adds story_key, id and type).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from . import text
from .limits import TRIGGER, Limit, extract_limits


@dataclass(frozen=True)
class StoryContext:
    """What every template needs to know about the story."""

    key: str
    feature: str            # "reset password", from the story title
    action: Optional[str]   # "reset the password", from "I want to ..."

    @classmethod
    def from_story(cls, story: dict) -> "StoryContext":
        title = text.sentence(str(story.get("title") or ""))
        return cls(
            key=str(story["key"]),
            feature=text.lower_first(title) if title else "",
            action=text.story_action(str(story.get("description") or "")),
        )

    @property
    def open_step(self) -> str:
        return f"Open the {self.feature} page" if self.feature else "Open the application"

    @property
    def feature_name(self) -> str:
        return self.feature or "application"

    @property
    def task(self) -> str:
        return self.action or f"use the {self.feature_name} feature"


@dataclass(frozen=True)
class Draft:
    title: str
    steps: Tuple[str, ...]
    expected: str


Template = Callable[[StoryContext, str], List[Draft]]


# --- functional: the normal path and one failure ---------------------------------

def functional(ctx: StoryContext, criterion: str) -> List[Draft]:
    statement = text.sentence(criterion)
    task = text.capitalize(ctx.task)
    return [
        Draft(
            title=text.capitalize(text.strip_article(statement)),
            steps=(ctx.open_step, f"{task} using valid data", "Check the result"),
            expected=text.capitalize(statement),
        ),
        Draft(
            title=f"Failure path: {text.lower_first(text.strip_article(statement))}",
            steps=(ctx.open_step, f"{task} using invalid or missing data", "Check the result"),
            expected=("The action is not completed, a clear error message is shown, "
                      f"and this does not happen: {text.lower_first(statement)}"),
        ),
    ]


# --- validation: one valid input and two invalid inputs ---------------------------

@dataclass(frozen=True)
class _Sample:
    entry: Optional[str]   # literal value to type; None means "leave the field empty"
    reason: str            # how the title describes it: "without an @ sign"


@dataclass(frozen=True)
class _FieldKind:
    pattern: str
    label: str
    valid: str
    invalid: Tuple[_Sample, _Sample]


# Checked in order, so "phone number" matches phone before number.
_FIELD_KINDS = (
    _FieldKind(r"e-?mail", "email address", "user@example.com",
               (_Sample("userexample.com", "without an @ sign"), _Sample("user@", "without a domain"))),
    _FieldKind(r"phone|mobile\s+number", "phone number", "+14155550123",
               (_Sample("12ab34", "containing letters"), _Sample("123", "with too few digits"))),
    _FieldKind(r"\bdate\b|birthday|date\s+of\s+birth", "date", "2026-10-20",
               (_Sample("2026-13-45", "that does not exist"), _Sample("20/10", "in the wrong format"))),
    _FieldKind(r"\burl\b|website|web\s+address", "URL", "https://example.com",
               (_Sample("example", "without a domain"), _Sample("htp:/example.com", "with a broken scheme"))),
    _FieldKind(r"card", "card number", "4111 1111 1111 1111",
               (_Sample("1234 5678", "with too few digits"), _Sample("abcd efgh ijkl mnop", "containing letters"))),
    _FieldKind(r"zip|postal|post\s*code", "postal code", "12345",
               (_Sample("ABCDE", "containing letters"), _Sample("12", "with too few characters"))),
    _FieldKind(r"password", "password", "Str0ng!Pass",
               (_Sample("abc", "that is too weak"), _Sample("        ", "made of spaces only"))),
    _FieldKind(r"quantity|amount|price|\bage\b|\bnumber\b|numeric", "number", "10",
               (_Sample("abc", "containing letters"), _Sample("-5", "that is negative"))),
    _FieldKind(r"\bname\b|username", "name", "Alex Morgan",
               (_Sample("<script>alert(1)</script>", "with forbidden characters"),
                _Sample("@@@###", "made of symbols only"))),
)
_REQUIRED_RE = re.compile(
    r"\b(?:required|mandatory|(?:must\s+not|cannot|can't|may\s+not)\s+be\s+(?:empty|blank|left\s+empty))\b",
    re.IGNORECASE,
)
_EMPTY = _Sample(None, "left empty")


def validation(ctx: StoryContext, criterion: str) -> List[Draft]:
    kind = _field_kind(criterion) or _field_kind(ctx.feature)
    field = text.subject(criterion) or (kind.label if kind else "input")
    if kind:
        valid_entry: str = f'"{kind.valid}"'
        invalid: Sequence[_Sample] = kind.invalid
    else:
        valid_entry = "a correctly formatted value"
        invalid = (_Sample(None, "in the wrong format"), _Sample(None, "with forbidden characters"))
    if _REQUIRED_RE.search(criterion):
        invalid = (_EMPTY, invalid[0])

    drafts = [Draft(
        title=f"Valid {field} is accepted",
        steps=(ctx.open_step, f"Enter {valid_entry} in the {field} field", "Submit the form"),
        expected=f"The {field} is accepted and the form can be submitted",
    )]
    for sample in invalid:
        drafts.append(Draft(
            title=text.capitalize(f"{field} {sample.reason} is rejected"),
            steps=(ctx.open_step, _invalid_entry_step(sample, field, kind is None), "Submit the form"),
            expected=f"The {field} is rejected and a clear validation message is shown next to the field",
        ))
    return drafts


def _field_kind(phrase: str) -> Optional[_FieldKind]:
    for kind in _FIELD_KINDS:
        if re.search(kind.pattern, phrase, re.IGNORECASE):
            return kind
    return None


def _invalid_entry_step(sample: _Sample, field: str, generic: bool) -> str:
    if sample is _EMPTY:
        return f"Leave the {field} field empty"
    if generic:
        return f"Enter a value {sample.reason} in the {field} field"
    return f'Enter "{sample.entry}" in the {field} field'


# --- boundary: just below, at and just above every limit --------------------------

_CONSTRAINT_RE = re.compile(
    r"\b(?:must|should|shall|has\s+to|have\s+to|needs?\s+to|cannot|can't|can|may|limited"
    r"|allowed|accepts?|only|required)\b",
    re.IGNORECASE,
)


def boundary(ctx: StoryContext, criterion: str) -> List[Draft]:
    limits = extract_limits(criterion)
    if not limits:
        return _boundary_without_number(ctx, criterion)

    subject = _subject_without_limit(criterion, limits) or "value"
    is_constraint = bool(_CONSTRAINT_RE.search(criterion))
    drafts: List[Draft] = []
    seen = set()
    for limit in limits:
        condition = limit.relation == TRIGGER or not is_constraint
        for value, inside in limit.probes():
            if (limit.unit, limit.currency, value) in seen:
                continue
            seen.add((limit.unit, limit.currency, value))
            quantity = limit.format(value)
            drafts.append(Draft(
                title=_boundary_title(limit, subject, quantity, inside, condition),
                steps=(ctx.open_step, _boundary_step(limit, subject, quantity, condition),
                       "Submit the form" if limit.kind == "length" else "Check the result"),
                expected=_boundary_expected(limit, subject, quantity, inside, condition, criterion),
            ))
    return drafts


def _subject_without_limit(criterion: str, limits: List[Limit]) -> Optional[str]:
    """"Orders over $50 get free shipping" -> "order", not "orders over $50"."""
    subject = text.subject(criterion)
    if not subject:
        return None
    for limit in limits:
        cut = subject.lower().find(limit.phrase.lower())
        if cut > 0:
            subject = subject[:cut].strip()
    return text.singular(subject)


def _boundary_title(limit: Limit, subject: str, quantity: str, inside: bool, condition: bool) -> str:
    if limit.relation == TRIGGER:
        return f"After {quantity}: rule applies" if inside else f"After only {quantity}: rule does not apply yet"
    if condition:
        outcome = "rule applies" if inside else "rule does not apply"
        return text.capitalize(f"{subject} with {quantity}: {outcome}")
    if limit.kind == "time":
        return text.capitalize(f"{subject} taking {quantity} {'passes' if inside else 'fails'} the limit")
    return text.capitalize(f"{subject} with {quantity} is {'accepted' if inside else 'rejected'}")


def _boundary_step(limit: Limit, subject: str, quantity: str, condition: bool) -> str:
    kind = limit.kind
    if kind == "length":
        return f"Enter {text.with_article(subject)} with {quantity}"
    if kind == "attempts":
        return f"Perform {quantity}"
    if kind == "repeat":
        return f"Repeat the action {quantity}"
    if kind == "items":
        return f"Add {quantity}"
    if kind == "time" and condition:
        return f"Wait {quantity}"
    if kind == "money":
        return f"Use an amount of {quantity}"
    return f"Use a value of {quantity} for the {subject}"


def _boundary_expected(limit: Limit, subject: str, quantity: str, inside: bool, condition: bool,
                       criterion: str) -> str:
    if condition:
        if inside:
            return f"The rule applies: {text.lower_first(text.sentence(criterion))}"
        return f"The rule does not apply, because {quantity} is outside the condition '{limit.phrase}'"
    if inside:
        return f"The {subject} is accepted because {quantity} is within the limit ({limit.phrase})"
    return f"The {subject} is rejected and an error message explains the limit ({limit.phrase})"


def _boundary_without_number(ctx: StoryContext, criterion: str) -> List[Draft]:
    subject = text.subject(criterion) or "value"
    statement = text.lower_first(text.sentence(criterion))
    return [
        Draft(
            title=text.capitalize(f"{subject} exactly at the limit is accepted"),
            steps=(ctx.open_step, f"Use the largest (or smallest) {subject} the rule allows", "Check the result"),
            expected=f"The {subject} is accepted because it respects the rule: {statement}",
        ),
        Draft(
            title=text.capitalize(f"{subject} just past the limit is rejected"),
            steps=(ctx.open_step, f"Use a {subject} one step past what the rule allows", "Check the result"),
            expected=f"The {subject} is rejected and an error message explains the rule: {statement}",
        ),
    ]


# --- security: an allowed user and a blocked user ---------------------------------

@dataclass(frozen=True)
class _Roles:
    allowed: str
    blocked: str


_ONLY_GROUP_RE = re.compile(
    r"\bonly\s+(?:the\s+)?(?P<group>[a-z]+(?:\s+[a-z]+)?)\s+(?:can|may|is|are|should|must|have|has)\b",
    re.IGNORECASE,
)
_PROTECTION_RE = re.compile(r"\b(?:encrypt\w*|hash\w*|https|tls|ssl|plain\s*text)\b", re.IGNORECASE)
_ANONYMOUS = "anonymous visitor (not logged in)"


def security(ctx: StoryContext, criterion: str) -> List[Draft]:
    roles = _roles(criterion)
    action = text.criterion_action(criterion) or ctx.task
    drafts = [
        Draft(
            title=text.capitalize(f"{roles.allowed} can {action}"),
            steps=(_login_step(roles.allowed), ctx.open_step, f"Try to {action}"),
            expected=f"Access is granted and the user can {action}",
        ),
        Draft(
            title=text.capitalize(f"{roles.blocked} cannot {action}"),
            steps=(_login_step(roles.blocked), ctx.open_step, f"Try to {action}"),
            expected=("Access is denied (error page, HTTP 403 or redirect to login), the action is not "
                      "performed and no protected data is shown"),
        ),
    ]
    if _PROTECTION_RE.search(criterion):
        drafts.append(Draft(
            title="Sensitive data is never stored or sent in plain text",
            steps=(_login_step(roles.allowed), f"{text.capitalize(action)}",
                   "Inspect the network traffic and the stored data"),
            expected="Traffic uses HTTPS and the sensitive data is stored only in encrypted or hashed form",
        ))
    return drafts


def _roles(criterion: str) -> _Roles:
    lowered = criterion.lower()
    if re.search(r"\badmin(?:istrator)?s?\b", lowered):
        return _Roles("administrator", "regular user (not an administrator)")
    if re.search(r"\bowners?\b|\btheir own\b|\bhis own\b|\bher own\b", lowered):
        return _Roles("owner of the data", "different logged-in user")
    only = _ONLY_GROUP_RE.search(criterion)
    if only:
        group = only["group"].lower()
        return _Roles(f"user in the '{group}' group", f"user outside the '{group}' group")
    if re.search(r"\blogged[\s-]in\b|\bauthenticated\b|\bsigned[\s-]in\b|\blog\s*in\b|\bsign\s*in\b", lowered):
        return _Roles("logged-in user", _ANONYMOUS)
    return _Roles("authorized user", "unauthorized user")


def _login_step(role: str) -> str:
    if role == _ANONYMOUS:
        return "Make sure no user is logged in"
    return f"Log in as {text.with_article(role)}"


# --- performance: one user, then under load ---------------------------------------

_LOAD_UNIT_RE = re.compile(r"\b(?:users?|requests?|sessions?|connections?|visitors?)\b", re.IGNORECASE)


def performance(ctx: StoryContext, criterion: str) -> List[Draft]:
    limits = extract_limits(criterion)
    time_limit = next((limit for limit in limits if limit.kind == "time"), None)
    load_limit = next((limit for limit in limits if _LOAD_UNIT_RE.search(limit.unit)), None)
    subject = text.subject(criterion) or ctx.feature_name
    load = load_limit.format(load_limit.high or load_limit.low) if load_limit else "100 concurrent users"
    statement = text.lower_first(text.sentence(criterion))

    if time_limit:
        single_expected = f"Every measurement is {time_limit.phrase}"
        load_expected = f"95% of requests are {time_limit.phrase} and no request fails"
    else:
        single_expected = f"The requirement holds: {statement}"
        load_expected = f"The requirement still holds under load ({statement}) and no request fails"

    return [
        Draft(
            title=text.capitalize(f"{subject} meets the target with a single user"),
            steps=(ctx.open_step, "Measure the response time with 1 user, 10 times in a row",
                   "Record the average and the slowest time"),
            expected=single_expected,
        ),
        Draft(
            title=text.capitalize(f"{subject} meets the target under load ({load})"),
            steps=(f"Prepare a load test (for example with JMeter or Locust) for the {ctx.feature_name} page",
                   f"Simulate {load} for 5 minutes",
                   "Record the 95th-percentile response time and the error rate"),
            expected=load_expected,
        ),
    ]


# --- usability: a first-time user, plus one ease-of-use check ---------------------

_MOBILE_RE = re.compile(r"\b(?:mobile|phone|tablet|responsive|small\s+screens?|screen\s+sizes?)\b", re.IGNORECASE)
_MESSAGE_RE = re.compile(r"\b(?:error|message|messages|feedback|confirm\w*|notification\w*|hint)\b", re.IGNORECASE)


def usability(ctx: StoryContext, criterion: str) -> List[Draft]:
    statement = text.lower_first(text.sentence(criterion))
    drafts = [Draft(
        title=f"First-time user can {ctx.task} without help",
        steps=(f"Give a first-time user this task: {ctx.task}", "Give no instructions or help",
               "Observe where the user hesitates or makes mistakes"),
        expected=f"The user completes the task without help, and this holds: {statement}",
    )]
    if _MOBILE_RE.search(criterion):
        drafts.append(Draft(
            title="Page works on a phone-sized screen",
            steps=(f"{ctx.open_step} on a screen 360 px wide", f"Try to {ctx.task}",
                   "Check the text, buttons and layout"),
            expected="All content fits the screen without sideways scrolling and every button is easy to tap",
        ))
    elif _MESSAGE_RE.search(criterion):
        drafts.append(Draft(
            title="Messages are clear and helpful",
            steps=(ctx.open_step, "Cause one successful and one failed attempt", "Read the messages shown"),
            expected="Each message says in plain words what happened and what to do next",
        ))
    else:
        drafts.append(Draft(
            title="Task can be completed with the keyboard only",
            steps=(ctx.open_step, f"Try to {ctx.task} using only Tab, Shift+Tab, Enter and Space",
                   "Watch the focus indicator"),
            expected="Every control can be reached and used with the keyboard and the focused element is always visible",
        ))
    return drafts


TEMPLATES: Dict[str, Template] = {
    "functional": functional,
    "validation": validation,
    "boundary": boundary,
    "security": security,
    "performance": performance,
    "usability": usability,
}
