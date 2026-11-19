from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from . import text
from .limits import TRIGGER, Limit, extract_limits


@dataclass(frozen=True)
class StoryContext:
    key: str
    feature: str
    action: Optional[str]
    persona: Optional[str] = None
    benefit: Optional[str] = None

    @classmethod
    def from_story(cls, story: dict) -> "StoryContext":
        title = text.sentence(str(story.get("title") or ""))
        desc = str(story.get("description") or "")
        return cls(
            key=str(story["key"]),
            feature=text.lower_first(title) if title else "",
            action=text.story_action(desc),
            persona=text.story_persona(desc),
            benefit=text.story_benefit(desc),
        )

    @property
    def open_step(self) -> str:
        if not self.feature:
            return "Open the application"
        clean = text.clean_page_name(self.feature)
        return f"Open the {clean}"

    @property
    def feature_name(self) -> str:
        return self.feature or "application"

    @property
    def task(self) -> str:
        return self.action or f"use the {self.feature_name} feature"

    @property
    def submit_step(self) -> str:
        return text.action_button(self.action or self.feature)


@dataclass(frozen=True)
class Draft:
    title: str
    input: str
    steps: Tuple[str, ...]
    expected: str
    priority: Optional[str] = None
    preconditions: Optional[Tuple[str, ...]] = None
    execution_type: Optional[str] = None


Template = Callable[[StoryContext, str], List[Draft]]


@dataclass(frozen=True)
class _Sample:
    entry: Optional[str]
    reason: str


@dataclass(frozen=True)
class _FieldKind:
    pattern: str
    label: str
    valid: str
    invalid: Tuple[_Sample, _Sample]
    existing: Optional[str] = None


_FIELD_KINDS = (
    _FieldKind(r"e-?mail", "email address", "user@example.com",
               (_Sample("userexample.com", "without an @ sign"), _Sample("user@", "without a domain")),
               existing="registered.user@example.com"),
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
    _FieldKind(r"address|street", "address", "123 Main Street",
               (_Sample("@@@###", "with forbidden symbols"), _Sample("", "left empty"))),
    _FieldKind(r"promo|coupon|discount\s+code", "promo code", "SAVE20",
               (_Sample("EXPIRED99", "that is expired"), _Sample("INVALID", "that does not exist"))),
    _FieldKind(r"search|query|keyword", "search query", "wireless headphones",
               (_Sample("<script>alert(1)</script>", "with injection characters"), _Sample("", "left empty"))),
)
_REQUIRED_RE = re.compile(
    r"\b(?:required|mandatory|(?:must\s+not|cannot|can't|may\s+not)\s+be\s+(?:empty|blank|left\s+empty))\b",
    re.IGNORECASE,
)
_EMPTY = _Sample(None, "left empty")


def validation(ctx: StoryContext, criterion: str) -> List[Draft]:
    kind = _field_kind(criterion) or _field_kind(ctx.feature)

    if kind:
        field = kind.label
    else:
        field = text.subject(criterion) or "input"
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
        input=f"{text.capitalize(field)}: {valid_entry}",
        steps=(ctx.open_step, f"Enter {valid_entry} in the {field} field", ctx.submit_step),
        expected=f"The {field} is accepted and the form can be submitted",
    )]
    for sample in invalid:
        drafts.append(Draft(
            title=text.capitalize(f"{field} {sample.reason} is rejected"),
            input=_invalid_input(sample, field),
            steps=(ctx.open_step, _invalid_entry_step(sample, field, kind is None), ctx.submit_step),
            expected=f"The {field} is rejected and a clear validation message is shown next to the field",
        ))
    return drafts


def _field_kind(phrase: str) -> Optional[_FieldKind]:
    for kind in _FIELD_KINDS:
        if re.search(kind.pattern, phrase, re.IGNORECASE):
            return kind
    return None


def _invalid_input(sample: _Sample, field: str) -> str:
    if sample is _EMPTY:
        return f"{text.capitalize(field)}: (empty)"
    if sample.entry is None:
        return f"{text.capitalize(field)}: a value {sample.reason}"
    return f'{text.capitalize(field)}: "{sample.entry}"'


def _invalid_entry_step(sample: _Sample, field: str, generic: bool) -> str:
    if sample is _EMPTY:
        return f"Leave the {field} field empty"
    if generic:
        return f"Enter a value {sample.reason} in the {field} field"
    return f'Enter "{sample.entry}" in the {field} field'


def functional(ctx: StoryContext, criterion: str) -> List[Draft]:
    statement = text.sentence(criterion)
    kind = _field_kind(criterion) or _field_kind(ctx.task) or _field_kind(ctx.feature)
    goal = text.lower_first(statement)
    if not kind:
        return _functional_without_field(ctx, statement)

    field = kind.label
    value = kind.existing or kind.valid
    wrong = kind.invalid[0]
    adjective = "registered" if kind.existing else "valid"
    return [
        Draft(
            title=text.capitalize(f"{adjective} {field}: {text.lower_first(text.strip_article(statement))}"),
            input=f'{text.capitalize(field)}: "{value}"',
            steps=(ctx.open_step, f'Enter the {adjective} {field} "{value}"', ctx.submit_step),
            expected=f"A confirmation message is shown and {goal}",
        ),
        Draft(
            title=text.capitalize(f"{field} {wrong.reason} is rejected"),
            input=f'{text.capitalize(field)}: "{wrong.entry}"',
            steps=(ctx.open_step, f'Enter "{wrong.entry}" in the {field} field', ctx.submit_step),
            expected=(f"The {field} is rejected, a validation error is shown next to the field, "
                      "and the form submission is blocked"),
        ),
        Draft(
            title=text.capitalize(f"empty {field} is rejected"),
            input=f'{text.capitalize(field)}: "" (empty)',
            steps=(ctx.open_step, f"Leave the {field} field empty", ctx.submit_step),
            expected=(f"The form is not submitted, and a required-field message is shown for the {field}"),
        ),
    ]


def _functional_without_field(ctx: StoryContext, statement: str) -> List[Draft]:
    task = text.capitalize(ctx.task)
    goal = text.lower_first(statement)
    return [
        Draft(
            title=text.capitalize(text.strip_article(statement)),
            input="All required fields: filled with correct values",
            steps=(ctx.open_step, "Fill every required field with a correct value", f"{task}"),
            expected=f"A confirmation message is shown and {goal}",
        ),
        Draft(
            title="One required field in the wrong format is rejected",
            input="One required field: a value in the wrong format, the other fields correct",
            steps=(ctx.open_step, "Fill one required field with a value in the wrong format "
                   "and the other fields correctly", f"{task}"),
            expected=("The action is not completed, and a validation error is shown next to the wrong field"),
        ),
        Draft(
            title="Empty required fields are rejected",
            input="All required fields: (empty)",
            steps=(ctx.open_step, "Leave every required field empty", f"{task}"),
            expected=("The action is not completed, and a required-field message is shown for each empty field"),
        ),
    ]


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
                input=_boundary_input(limit, subject, quantity, value),
                steps=(ctx.open_step, _boundary_step(limit, subject, quantity, condition, value),
                       ctx.submit_step if limit.kind == "length" else "Check the result"),
                expected=_boundary_expected(limit, subject, quantity, inside, condition, criterion, value),
            ))
    return drafts


def _subject_without_limit(criterion: str, limits: List[Limit]) -> Optional[str]:
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


def _boundary_input(limit: Limit, subject: str, quantity: str, value: Decimal) -> str:
    if limit.kind in ("attempts", "repeat", "items"):
        return text.capitalize(quantity)
    sample = _length_sample(limit, subject, value)
    if sample is not None:
        return text.capitalize(f"{subject}: {sample} ({quantity})")
    return text.capitalize(f"{subject}: {quantity}")


_PASSWORD_CHARS = "Passw0rd!Secure#2026Key"
_DIGIT_CHARS = "1234567890"
_LETTER_CHARS = "abcdefghijklmnopqrstuvwxyz"
_LONGEST_LITERAL = 30


def _length_sample(limit: Limit, subject: str, value: Decimal) -> Optional[str]:
    if limit.kind != "length" or value != value.to_integral_value() or limit.unit.split()[-1] in ("word", "words"):
        return None
    count = int(value)
    if count == 0:
        return '""'
    if "digit" in limit.unit:
        chars = _DIGIT_CHARS
    elif "password" in subject.lower():
        chars = _PASSWORD_CHARS
    else:
        chars = _LETTER_CHARS
    if count > _LONGEST_LITERAL:
        return f'"{chars[0]}" repeated {count} times'
    return '"' + (chars * (count // len(chars) + 1))[:count] + '"'


def _boundary_step(limit: Limit, subject: str, quantity: str, condition: bool, value: Decimal) -> str:
    kind = limit.kind
    if kind == "length":
        sample = _length_sample(limit, subject, value)
        if sample is not None:
            return f"Enter {sample} ({quantity}) in the {subject} field"
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
                       criterion: str, value: Decimal) -> str:
    verb = "are" if limit.unit.endswith("s") else "is"
    if condition:
        if inside:
            return f"The rule applies: {text.lower_first(text.sentence(criterion))}"
        return f"The condition is not triggered: {quantity} does not meet '{limit.phrase}'"
    if limit.kind == "length":
        if inside:
            if limit.low is not None and value == limit.low:
                qualifier = f"at the exact minimum threshold ({limit.phrase})"
            elif limit.high is not None and value == limit.high:
                qualifier = f"at the maximum allowed limit ({limit.phrase})"
            elif limit.low is not None and value > limit.low:
                qualifier = f"above the minimum threshold ({limit.phrase})"
            else:
                qualifier = f"within the required limit ({limit.phrase})"
            return f"The {subject} is accepted {qualifier}, the form is submitted successfully and confirmation is shown"
        return (f"The {subject} is rejected, the form is not submitted and a validation error "
                f"indicates that {limit.phrase} {verb} required")
    if inside:
        if limit.low is not None and value == limit.low:
            return f"The {subject} is accepted at the minimum threshold of {limit.phrase}"
        if limit.high is not None and value == limit.high:
            return f"The {subject} is accepted at the maximum threshold of {limit.phrase}"
        return f"The {subject} is accepted within the allowed threshold of {limit.phrase}"
    return f"The {subject} is rejected and an error message explains the rule: {limit.phrase}"


def _boundary_without_number(ctx: StoryContext, criterion: str) -> List[Draft]:
    subject = text.subject(criterion) or "value"
    statement = text.lower_first(text.sentence(criterion))
    return [
        Draft(
            title=text.capitalize(f"{subject} exactly at the limit is accepted"),
            input=text.capitalize(f"{subject}: exactly at the limit"),
            steps=(ctx.open_step, f"Use the largest (or smallest) {subject} the rule allows", "Check the result"),
            expected=f"The {subject} is accepted in accordance with the rule: {statement}",
        ),
        Draft(
            title=text.capitalize(f"{subject} just past the limit is rejected"),
            input=text.capitalize(f"{subject}: one step past the limit"),
            steps=(ctx.open_step, f"Use a {subject} one step past what the rule allows", "Check the result"),
            expected=f"The {subject} is rejected and a validation error explains the rule: {statement}",
        ),
    ]


@dataclass(frozen=True)
class _Roles:
    allowed: str
    blocked: str
    allowed_account: str
    blocked_account: Optional[str]


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
            input=_user_input(roles.allowed, roles.allowed_account),
            steps=(_login_step(roles.allowed, roles.allowed_account), ctx.open_step, f"Try to {action}"),
            expected=f"Access is granted and the user can {action}",
        ),
        Draft(
            title=text.capitalize(f"{roles.blocked} cannot {action}"),
            input=_user_input(roles.blocked, roles.blocked_account),
            steps=(_login_step(roles.blocked, roles.blocked_account), ctx.open_step, f"Try to {action}"),
            expected=("Access is denied (error page, HTTP 403 or redirect to login), the action is not "
                      "performed and no protected data is shown"),
        ),
    ]
    if _PROTECTION_RE.search(criterion):
        drafts.append(Draft(
            title="Sensitive data is never stored or sent in plain text",
            input=f'{_user_input(roles.allowed, roles.allowed_account)}, password "Str0ng!Pass"',
            steps=(_login_step(roles.allowed, roles.allowed_account), f"{text.capitalize(action)}",
                   "Inspect the network traffic and the stored data"),
            expected="Traffic uses HTTPS and the sensitive data is stored only in encrypted or hashed form",
        ))
    return drafts


def _roles(criterion: str) -> _Roles:
    lowered = criterion.lower()
    if re.search(r"\badmin(?:istrator)?s?\b", lowered):
        return _Roles("administrator", "regular user (not an administrator)",
                      "admin@example.com", "user@example.com")
    if re.search(r"\bowners?\b|\btheir own\b|\bhis own\b|\bher own\b", lowered):
        return _Roles("owner of the data", "different logged-in user",
                      "owner@example.com", "other.user@example.com")
    only = _ONLY_GROUP_RE.search(criterion)
    if only:
        group = only["group"].lower()
        return _Roles(f"user in the '{group}' group", f"user outside the '{group}' group",
                      f"{re.sub(r'[^a-z]+', '.', group)}.member@example.com", "outsider@example.com")
    if re.search(r"\blogged[\s-]in\b|\bauthenticated\b|\bsigned[\s-]in\b|\blog\s*in\b|\bsign\s*in\b", lowered):
        return _Roles("logged-in user", _ANONYMOUS, "user@example.com", None)
    return _Roles("authorized user", "unauthorized user",
                  "authorized.user@example.com", "unauthorized.user@example.com")


def _user_input(role: str, account: Optional[str]) -> str:
    return f"User: {role} ({account})" if account else f"User: {role}"


def _login_step(role: str, account: Optional[str]) -> str:
    if account is None:
        return "Make sure no user is logged in"
    return f"Log in as {text.with_article(role)} ({account})"


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
            input="1 user, 10 requests in a row",
            steps=(ctx.open_step, "Measure the response time with 1 user, 10 times in a row",
                   "Record the average and the slowest time"),
            expected=single_expected,
        ),
        Draft(
            title=text.capitalize(f"{subject} meets the target under load ({load})"),
            input=f"{load} for 5 minutes",
            steps=(f"Prepare a load test (for example with JMeter or Locust) for the {ctx.feature_name} page",
                   f"Simulate {load} for 5 minutes",
                   "Record the 95th-percentile response time and the error rate"),
            expected=load_expected,
        ),
    ]


_MOBILE_RE = re.compile(r"\b(?:mobile|phone|tablet|responsive|small\s+screens?|screen\s+sizes?)\b", re.IGNORECASE)
_MESSAGE_RE = re.compile(r"\b(?:error|message|messages|feedback|confirm\w*|notification\w*|hint)\b", re.IGNORECASE)


def usability(ctx: StoryContext, criterion: str) -> List[Draft]:
    statement = text.lower_first(text.sentence(criterion))
    persona = ctx.persona or "user"
    drafts = [Draft(
        title=f"First-time {persona} can {ctx.task} without help",
        input=f"A first-time {persona}, no instructions",
        steps=(f"Give a first-time {persona} this task: {ctx.task}", "Give no instructions or help",
               "Observe where the user hesitates or makes mistakes"),
        expected=f"The {persona} completes the task without help, and this holds: {statement}",
    )]
    if _MOBILE_RE.search(criterion):
        drafts.append(Draft(
            title="Page works on a phone-sized screen",
            input="Screen width: 360 px",
            steps=(f"{ctx.open_step} on a screen 360 px wide", f"Try to {ctx.task}",
                   "Check the text, buttons and layout"),
            expected="All content fits the screen without sideways scrolling and every button is easy to tap",
        ))
    elif _MESSAGE_RE.search(criterion):
        drafts.append(Draft(
            title="Messages are clear and helpful",
            input="One successful and one failed attempt",
            steps=(ctx.open_step, "Cause one successful and one failed attempt", "Read the messages shown"),
            expected="Each message says in plain words what happened and what to do next",
        ))
    else:
        drafts.append(Draft(
            title="Task can be completed with the keyboard only",
            input="Keyboard only: Tab, Shift+Tab, Enter and Space",
            steps=(ctx.open_step, f"Try to {ctx.task} using only Tab, Shift+Tab, Enter and Space",
                   "Watch the focus indicator"),
            expected="Every control can be reached and used with the keyboard and the focused element is always visible",
        ))
    return drafts


_RECOVERY_RE = re.compile(
    r"\b(?:recover|retry|reconnect|restore|resume|failover|fall\s*back|backup|redundan|replicat)\b",
    re.IGNORECASE,
)
_AVAILABILITY_RE = re.compile(
    r"\b(?:uptime|availab|SLA|99(?:\.\d+)?%|24/7|always\s+(?:on|available)|downtime)\b",
    re.IGNORECASE,
)


def reliability(ctx: StoryContext, criterion: str) -> List[Draft]:
    statement = text.lower_first(text.sentence(criterion))
    subject = text.subject(criterion) or ctx.feature_name

    drafts = [Draft(
        title=text.capitalize(f"{subject} works correctly under normal conditions"),
        input="Normal operating conditions, stable network",
        steps=(ctx.open_step, f"Use the {ctx.feature_name} feature under normal conditions",
               "Verify the operation completes successfully"),
        expected=f"The operation completes without errors and the requirement holds: {statement}",
    )]

    if _RECOVERY_RE.search(criterion):
        drafts.append(Draft(
            title=text.capitalize(f"{subject} recovers after a failure"),
            input="Simulated failure: network disconnection or service restart",
            steps=(ctx.open_step, f"Trigger a failure while using the {ctx.feature_name} feature "
                   "(e.g. disconnect the network or restart a dependent service)",
                   "Wait for the system to detect the failure",
                   "Verify that the system recovers automatically or provides clear recovery steps"),
            expected=f"The system recovers gracefully, no data is lost, and the requirement holds: {statement}",
        ))
    elif _AVAILABILITY_RE.search(criterion):
        drafts.append(Draft(
            title=text.capitalize(f"{subject} remains available during extended operation"),
            input="Extended operation: 24+ hours of continuous use",
            steps=("Run the system under typical load for an extended period (24+ hours)",
                   "Monitor for crashes, memory leaks and service interruptions",
                   "Record any downtime or degraded performance"),
            expected=f"The system remains available throughout the test period and the requirement holds: {statement}",
        ))
    else:
        drafts.append(Draft(
            title=text.capitalize(f"{subject} handles unexpected failures gracefully"),
            input="Simulated failure: unexpected error or service interruption",
            steps=(ctx.open_step, "Simulate an unexpected failure (e.g. kill a backend process, "
                   "inject a database timeout or corrupt a network response)",
                   "Observe the system's response"),
            expected=(f"The system does not crash, shows a clear error message to the user, "
                      f"preserves existing data and can resume normal operation"),
        ))

    return drafts


_BROWSER_RE = re.compile(
    r"\b(?:browsers?|chrome|firefox|safari|edge|opera|IE|internet\s+explorer)\b",
    re.IGNORECASE,
)
_OS_RE = re.compile(
    r"\b(?:windows|linux|mac(?:os)?|android|ios|operating\s+systems?|cross[\s-]platform)\b",
    re.IGNORECASE,
)
_DEVICE_RE = re.compile(
    r"\b(?:devices?|desktops?|laptops?|tablets?|phones?|mobile|wearables?|smart\s*(?:phones?|watch(?:es)?|tv))\b",
    re.IGNORECASE,
)


def portability(ctx: StoryContext, criterion: str) -> List[Draft]:
    statement = text.lower_first(text.sentence(criterion))
    subject = text.subject(criterion) or ctx.feature_name

    if _BROWSER_RE.search(criterion):
        drafts = [
            Draft(
                title=text.capitalize(f"{subject} works in Chrome (primary browser)"),
                input="Browser: Google Chrome (latest stable version)",
                steps=(f"Open {ctx.feature_name} in the latest stable Chrome",
                       f"Try to {ctx.task}", "Verify all features work correctly"),
                expected=f"All features work correctly in Chrome and the requirement holds: {statement}",
            ),
            Draft(
                title=text.capitalize(f"{subject} works in Firefox and Safari"),
                input="Browsers: Firefox (latest stable), Safari (latest stable)",
                steps=(f"Open {ctx.feature_name} in Firefox and repeat the test",
                       f"Open {ctx.feature_name} in Safari and repeat the test",
                       "Compare the behaviour, layout and functionality with Chrome"),
                expected=(f"The feature behaves identically in Firefox and Safari, with no layout "
                          f"differences or broken functionality"),
            ),
        ]
    elif _OS_RE.search(criterion):
        drafts = [
            Draft(
                title=text.capitalize(f"{subject} works on the primary operating system"),
                input="OS: Windows 11 (or the project's primary OS)",
                steps=(f"Install or open {ctx.feature_name} on the primary OS",
                       f"Try to {ctx.task}", "Verify all features work correctly"),
                expected=f"All features work correctly on the primary OS and the requirement holds: {statement}",
            ),
            Draft(
                title=text.capitalize(f"{subject} works on a different operating system"),
                input="OS: macOS or Linux (a secondary platform)",
                steps=(f"Install or open {ctx.feature_name} on a secondary OS (macOS or Linux)",
                       f"Try to {ctx.task}",
                       "Compare the behaviour with the primary OS"),
                expected=(f"The feature behaves correctly on the secondary OS with no platform-specific "
                          f"errors or missing functionality"),
            ),
        ]
    elif _DEVICE_RE.search(criterion):
        drafts = [
            Draft(
                title=text.capitalize(f"{subject} works on a desktop device"),
                input="Device: desktop or laptop with standard screen",
                steps=(f"Open {ctx.feature_name} on a desktop or laptop",
                       f"Try to {ctx.task}", "Verify all features work correctly"),
                expected=f"All features work correctly on a desktop device and the requirement holds: {statement}",
            ),
            Draft(
                title=text.capitalize(f"{subject} works on a mobile device"),
                input="Device: smartphone or tablet",
                steps=(f"Open {ctx.feature_name} on a smartphone or tablet",
                       f"Try to {ctx.task}",
                       "Compare the behaviour with the desktop version"),
                expected=(f"The feature works correctly on mobile, with appropriate touch interactions "
                          f"and readable layout"),
            ),
        ]
    else:
        drafts = [
            Draft(
                title=text.capitalize(f"{subject} works in the primary environment"),
                input="Primary deployment environment (production-like setup)",
                steps=(f"Deploy or open {ctx.feature_name} in the primary environment",
                       f"Try to {ctx.task}", "Verify all features work correctly"),
                expected=f"All features work correctly in the primary environment and the requirement holds: {statement}",
            ),
            Draft(
                title=text.capitalize(f"{subject} works in an alternative environment"),
                input="Alternative environment (different browser, OS or device)",
                steps=(f"Deploy or open {ctx.feature_name} in an alternative environment "
                       "(different browser, OS or device)",
                       f"Try to {ctx.task}",
                       "Compare the behaviour with the primary environment"),
                expected=(f"The feature behaves correctly in the alternative environment with no "
                          f"platform-specific errors or degraded functionality"),
            ),
        ]

    return drafts


_CONFIG_RE = re.compile(
    r"\b(?:config\w*|setting|parameter|variable|environment|env\s*var|toggle|feature\s+flag)\b",
    re.IGNORECASE,
)
_LOG_RE = re.compile(
    r"\b(?:log|logging|trace|audit\s+trail|monitor|debug|diagnostic)\b",
    re.IGNORECASE,
)
_DOC_RE = re.compile(
    r"\b(?:document\w*|comment\w*|readme|wiki|API\s+doc|changelog|release\s+note)\b",
    re.IGNORECASE,
)
_MODULAR_RE = re.compile(
    r"\b(?:modular|module|component|decouple|loosely\s+coupled|separat|encapsulat|refactor|extend)\b",
    re.IGNORECASE,
)


def maintainability(ctx: StoryContext, criterion: str) -> List[Draft]:
    statement = text.lower_first(text.sentence(criterion))
    subject = text.subject(criterion) or ctx.feature_name

    if _CONFIG_RE.search(criterion):
        drafts = [
            Draft(
                title=text.capitalize(f"{subject} can be changed without modifying code"),
                input="Configuration: a changed setting value (e.g. timeout, threshold or feature flag)",
                steps=("Identify the configuration parameter described in the requirement",
                       "Change its value via config file, environment variable or admin panel",
                       "Restart or reload the application and verify the change takes effect"),
                expected=f"The change takes effect without code modification and the requirement holds: {statement}",
            ),
            Draft(
                title=text.capitalize(f"Invalid {subject} configuration is handled safely"),
                input="Configuration: an invalid or missing value",
                steps=("Set the configuration parameter to an invalid value (or remove it entirely)",
                       "Restart or reload the application",
                       "Observe whether the system uses a safe default or shows a clear error"),
                expected=("The system either falls back to a safe default or refuses to start with "
                          "a clear error message; it never silently uses the invalid value"),
            ),
        ]
    elif _LOG_RE.search(criterion):
        drafts = [
            Draft(
                title=text.capitalize(f"{subject} produces useful log entries"),
                input="One successful and one failed operation",
                steps=(f"Perform a successful {ctx.task}",
                       f"Perform a failing {ctx.task} (e.g. with invalid input)",
                       "Inspect the application logs for both operations"),
                expected=f"Each operation is logged with enough detail to diagnose issues, and the requirement holds: {statement}",
            ),
            Draft(
                title=text.capitalize(f"Sensitive data is not exposed in {subject}"),
                input="Operation involving sensitive data (passwords, tokens, PII)",
                steps=("Perform an operation that involves sensitive data",
                       "Inspect the application logs",
                       "Search for any passwords, tokens or personally identifiable information"),
                expected="No sensitive data appears in the logs in plain text",
            ),
        ]
    elif _DOC_RE.search(criterion):
        drafts = [
            Draft(
                title=text.capitalize(f"{subject} exists and is up to date"),
                input="Current codebase and feature set",
                steps=("Locate the documentation for the feature or component",
                       "Compare the documentation against the current code and behaviour",
                       "Check for missing sections, outdated instructions or broken examples"),
                expected=f"The documentation accurately describes the current behaviour and the requirement holds: {statement}",
            ),
            Draft(
                title=text.capitalize(f"A new team member can understand {subject}"),
                input="A developer unfamiliar with the codebase",
                steps=("Give a developer unfamiliar with the codebase only the documentation",
                       "Ask them to explain how the feature works or to make a small change",
                       "Observe whether the documentation is sufficient"),
                expected="The developer can understand the feature and make a change using only the documentation",
            ),
        ]
    elif _MODULAR_RE.search(criterion):
        drafts = [
            Draft(
                title=text.capitalize(f"{subject} can be modified independently"),
                input="A small change to one module or component",
                steps=("Identify the module or component described in the requirement",
                       "Make a small change to it (e.g. add a field, change a label)",
                       "Run the existing tests and verify that unrelated modules are not affected"),
                expected=f"The change is isolated to the target module, all tests pass, and the requirement holds: {statement}",
            ),
            Draft(
                title=text.capitalize(f"Changing {subject} does not break other features"),
                input="A change to the module followed by a full regression test",
                steps=("Make a change to the module or component",
                       "Run the full test suite",
                       "Verify that no unrelated tests fail"),
                expected="All unrelated tests continue to pass and no side effects are observed",
            ),
        ]
    else:
        drafts = [
            Draft(
                title=text.capitalize(f"{subject} can be updated with minimal effort"),
                input="A small functional change to the feature",
                steps=("Identify the code or component responsible for the feature",
                       "Make a small change (e.g. add a field, adjust a rule)",
                       "Run the existing tests and verify the change works"),
                expected=f"The change is straightforward, tests pass, and the requirement holds: {statement}",
            ),
            Draft(
                title=text.capitalize(f"Modifying {subject} does not introduce regressions"),
                input="A change to the feature followed by a full regression test",
                steps=("Make a change to the feature",
                       "Run the full test suite (unit, integration and end-to-end)",
                       "Review test results for unexpected failures"),
                expected="All existing tests continue to pass and no regressions are introduced",
            ),
        ]

    return drafts


TEMPLATES: Dict[str, Template] = {
    "functional": functional,
    "validation": validation,
    "boundary": boundary,
    "security": security,
    "performance": performance,
    "usability": usability,
    "reliability": reliability,
    "portability": portability,
    "maintainability": maintainability,
}
