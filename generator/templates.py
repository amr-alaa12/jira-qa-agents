"""One test-case template per requirement category.

Each template takes the story context and one acceptance criterion and
returns at least two drafts. The core module turns drafts into test cases
in the agreed format (adds story_key, id and type).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from . import text
from .limits import PREFIX_RE, TRIGGER, Limit, extract_limits


@dataclass(frozen=True)
class StoryContext:
    """What every template needs to know about the story."""

    key: str
    feature: str            # "reset password", from the story title
    action: Optional[str]   # "reset the password", from "I want to ..."

    @classmethod
    def from_story(cls, story: dict) -> "StoryContext":
        title = text.sentence(str(story.get("title") or ""))
        title_action = text.story_action(title)   # title written as "As a user, I want to ..."
        action = text.story_action(str(story.get("description") or "")) or title_action
        if title_action:
            title = ""   # not a feature name: avoid "Open the As a user ... page"
        title = _feature_from_title(title)
        return cls(
            key=str(story["key"]),
            feature=text.lower_first(title) if title else "",
            action=action,
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


# Story titles often start with the task's verb ("Manage user accounts"); the page is named
# after what follows it ("the user accounts page"). Kept to verbs that are rarely nouns in titles.
_TITLE_VERBS = {
    "manage", "send", "respect", "export", "import", "write", "create", "view", "add", "edit", "delete",
    "update", "place", "make", "allow", "show", "use", "get", "track", "submit", "approve", "upload",
    "download", "cancel", "filter", "sort", "configure", "enable", "disable", "display", "generate",
    "receive", "share", "assign", "remove", "browse", "select", "choose", "change", "save", "book",
    "schedule", "invite", "notify", "handle", "support", "provide", "integrate", "sync", "pay", "buy",
}


def _feature_from_title(title: str) -> str:
    """ "Manage user accounts" -> "user accounts"; "Reset password" and "Checkout" stay as they are."""
    words = title.split()
    if len(words) >= 2 and words[0].lower() in _TITLE_VERBS:
        rest = text.strip_article(" ".join(words[1:]))
        return re.split(r"\s+(?:using|with|by|for|from|via|through|in|on|to|into)\s+", rest, maxsplit=1)[0]
    return title


@dataclass(frozen=True)
class Draft:
    title: str
    input: str               # the test data: "New password: 7 characters"
    steps: Tuple[str, ...]
    expected_output: str


Template = Callable[[StoryContext, str], List[Draft]]


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
    existing: Optional[str] = None   # a value the system already knows, for the normal path


# Checked in order, so "phone number" matches phone before number.
_FIELD_KINDS = (
    _FieldKind(r"e-?mail(?!\s+(?:notifications?|messages?|alerts?|reminders?|confirmations?|digests?"
               r"|campaigns?|templates?|updates?|reports?|summary|summaries))", "email address", "user@example.com",
               (_Sample("userexample.com", "without an @ sign"), _Sample("user@", "without a domain")),
               existing="registered.user@example.com"),
    _FieldKind(r"\bphone\b|\bmobile\s+number\b", "phone number", "+14155550123",
               (_Sample("12ab34", "containing letters"), _Sample("123", "with too few digits"))),
    _FieldKind(r"\bdate\b|birthday|date\s+of\s+birth", "date", "2026-10-20",
               (_Sample("2026-13-45", "that does not exist"), _Sample("20/10", "in the wrong format"))),
    _FieldKind(r"\burl\b|website|web\s+address", "URL", "https://example.com",
               (_Sample("example", "without a domain"), _Sample("htp:/example.com", "with a broken scheme"))),
    _FieldKind(r"\bcard\b", "card number", "4111 1111 1111 1111",
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

    if kind:
        field = kind.label
    else:
        field = _field_name(criterion)
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
        steps=(ctx.open_step, f"Enter {valid_entry} in the {field} field", "Submit the form"),
        expected_output=f"The {field} is accepted and the form can be submitted",
    )]
    for sample in invalid:
        drafts.append(Draft(
            title=text.capitalize(f"{field} {sample.reason} is rejected"),
            input=_invalid_input(sample, field),
            steps=(ctx.open_step, _invalid_entry_step(sample, field, kind is None), "Submit the form"),
            expected_output=f"The {field} is rejected and a clear validation message is shown next to the field",
        ))
    return drafts


_NOT_A_FIELD = {"system", "user", "users", "application", "app", "page", "form", "site", "website", "customer",
                "admin", "administrator", "it", "this", "that", "they", "we", "you"}


def _field_name(criterion: str) -> str:
    """The field a validation criterion is about; an actor ("the system") is not a field.

    "Given the payment information is invalid, when ..., then the system should reject it"
    -> "payment information".
    """
    for candidate in (text.subject(criterion), text.subject(text.precondition(criterion) or "")):
        if candidate and candidate.lower() not in _NOT_A_FIELD and not candidate.lower().startswith("the user"):
            return candidate
    return "input"


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


# --- functional: the normal path, a wrong value and an empty value ----------------

def functional(ctx: StoryContext, criterion: str) -> List[Draft]:
    """Each case names the exact value typed, so a tester can run it as written.

    The negative cases assert the logical opposite of the criterion's outcome
    ("the review is not saved"), never the outcome itself.
    """
    statement = text.about_user(text.outcome(criterion))
    kind = _field_kind(criterion) or _field_kind(ctx.task) or _field_kind(ctx.feature)
    setup = _precondition_steps(ctx, criterion)
    if not kind:
        return _functional_without_field(ctx, statement, setup)

    field = kind.label
    value = kind.existing or kind.valid
    wrong = kind.invalid[0]
    adjective = "registered" if kind.existing else "valid"
    return [
        Draft(
            title=text.capitalize(f"{adjective} {field}: {text.lower_first(text.strip_article(statement))}"),
            input=f'{text.capitalize(field)}: "{value}"',
            steps=(*setup, f'Enter the {adjective} {field} "{value}"', "Submit the form"),
            expected_output=_success_expected(statement),
        ),
        Draft(
            title=text.capitalize(f"{field} {wrong.reason} is rejected"),
            input=f'{text.capitalize(field)}: "{wrong.entry}"',
            steps=(*setup, f'Enter "{wrong.entry}" in the {field} field', "Submit the form"),
            expected_output=_failure_expected(
                [f"The {field} is rejected", "a validation error is shown next to the field"], statement),
        ),
        Draft(
            title=text.capitalize(f"empty {field} is rejected"),
            input=f'{text.capitalize(field)}: "" (empty)',
            steps=(*setup, f"Leave the {field} field empty", "Submit the form"),
            expected_output=_failure_expected(
                ["The form is not submitted", f"a required-field message is shown for the {field}"], statement),
        ),
    ]


def _functional_without_field(ctx: StoryContext, statement: str, setup: Tuple[str, ...]) -> List[Draft]:
    """No known field in the story, so the input names which fields are filled and how."""
    task = text.capitalize(ctx.task)
    return [
        Draft(
            title=text.capitalize(text.strip_article(text.affirm(statement))),
            input="All required fields: filled with correct values",
            steps=(*setup, "Fill every required field with a correct value", f"{task}"),
            expected_output=_success_expected(statement),
        ),
        Draft(
            title="One required field in the wrong format is rejected",
            input="One required field: a value in the wrong format, the other fields correct",
            steps=(*setup, "Fill one required field with a value in the wrong format "
                   "and the other fields correctly", f"{task}"),
            expected_output=_failure_expected(
                ["The action is not completed", "a validation error is shown next to the wrong field"], statement),
        ),
        Draft(
            title="Empty required fields are rejected",
            input="All required fields: (empty)",
            steps=(*setup, "Leave every required field empty", f"{task}"),
            expected_output=_failure_expected(
                ["The action is not completed", "a required-field message is shown for each empty field"],
                statement),
        ),
    ]


def _precondition_steps(ctx: StoryContext, criterion: str) -> Tuple[str, ...]:
    """Open the page, then set up the criterion's "Given" state so every case starts from it."""
    given = text.precondition(criterion)
    return (ctx.open_step, f"Make sure that {given}") if given else (ctx.open_step,)


def _success_expected(statement: str) -> str:
    """Valid input: the criterion's outcome is observed.

    A criterion that describes an error path ("the payment is rejected") gets no
    confirmation message, which would contradict it.
    """
    observed = text.affirm(statement)
    if text.is_failure_outcome(statement):
        return text.capitalize(observed)
    return f"A confirmation message is shown and {text.lower_first(observed)}"


def _failure_expected(rejection: List[str], statement: str) -> str:
    """Invalid input: the action is rejected and the criterion's outcome does NOT occur.

    - success outcome  -> its logical opposite is asserted ("the review is not saved");
    - error-path outcome -> nothing is added: negating "an error is shown" would contradict
      the rejection itself;
    - permission ("customers can edit their review") -> nothing is added: a failed form does not
      take the right away;
    - outcome that cannot be negated safely -> it is quoted as the result that must not occur.
    """
    parts = list(rejection)
    if not text.is_failure_outcome(statement) and not text.is_permission(statement):
        negated = text.negate(statement)
        if negated:
            parts.append(text.lower_first(negated))
        else:
            parts.append(f"the expected result (\"{text.lower_first(text.sentence(statement))}\") does not occur")
    if len(parts) == 2:
        return f"{parts[0]} and {parts[1]}"
    return f"{', '.join(parts[:-1])}, and {parts[-1]}"


# --- boundary: just below, at and just above every limit --------------------------

_CONSTRAINT_RE = re.compile(
    r"\b(?:must|should|shall|has\s+to|have\s+to|needs?\s+to|cannot|can't|can|may|limited"
    r"|allowed|accept(?:s|ed)?|only|required)\b",
    re.IGNORECASE,
)


def boundary(ctx: StoryContext, criterion: str) -> List[Draft]:
    limits = extract_limits(criterion)
    if not limits:
        return _boundary_without_number(ctx, criterion)

    subject = _subject_without_limit(criterion, limits) or "value"
    is_constraint = bool(_CONSTRAINT_RE.search(criterion))
    permission = _permission(criterion, limits)
    drafts: List[Draft] = []
    seen = set()
    for limit in limits:
        condition = limit.relation == TRIGGER or not is_constraint
        for value, inside in limit.probes():
            if (limit.unit, limit.currency, value) in seen:
                continue
            seen.add((limit.unit, limit.currency, value))
            quantity = limit.format(value)
            if permission and not condition:
                drafts.append(_permission_draft(ctx, permission, limit, quantity, inside))
                continue
            drafts.append(Draft(
                title=_boundary_title(limit, subject, quantity, inside, condition),
                input=_boundary_input(limit, subject, quantity, value),
                steps=(ctx.open_step, _boundary_step(limit, subject, quantity, condition, value),
                       "Submit the form" if limit.kind == "length" else "Check the result"),
                expected_output=_boundary_expected(limit, subject, quantity, inside, condition, criterion),
            ))
    return drafts


_PERSON_RE = re.compile(
    r"\b(?:users?|customers?|admins?|administrators?|managers?|members?|buyers?|sellers?|visitors?|guests?"
    r"|students?|employees?|clients?|drivers?|owners?|staff|agents?|shoppers?|subscribers?|patients?|teachers?"
    r"|editors?|authors?|operators?|leads?|people|person|account\s+holders?)\b",
    re.IGNORECASE,
)


_DENIED_ACTION_RE = re.compile(
    r"\b(?:cannot|can't|can\s+not|must\s+not|may\s+not|(?:is|are)\s+not\s+allowed\s+to)\s+(?P<action>.+)$",
    re.IGNORECASE,
)


def _permission(criterion: str, limits: List[Limit]) -> Optional[Tuple[str, str]]:
    """(actor, action) for a limit on what a person may do.

    "Customers can cancel an order within 24 hours"        -> ("customer", "cancel an order")
    "A user cannot have more than 5 active sessions"       -> ("user", "have")
    """
    actor = text.subject(criterion)
    if not actor or not _PERSON_RE.search(actor):
        return None
    action = text.criterion_action(criterion)
    if not action:
        denied = _DENIED_ACTION_RE.search(text.sentence(criterion))
        action = denied["action"] if denied else None
    if not action or action.lower().startswith("be "):
        return None
    number = re.search(r"[$€£]?\d", action)
    if number:   # keep only the words before the limit: "cancel an order [within 24 hours]"
        head = action[:number.start()]
        qualifier = PREFIX_RE.search(head)
        action = head[:qualifier.start()] if qualifier else head
    action = re.sub(r"\s+", " ", action).strip(" ,")
    return (actor, action) if action else None


def _permission_draft(ctx: StoryContext, permission: Tuple[str, str], limit: Limit, quantity: str,
                      inside: bool) -> Draft:
    """A limit on what a person may do: the action is allowed inside the limit and refused outside it."""
    actor, action = permission
    if limit.kind == "time":
        doing = f"{action} after {quantity}"
    elif limit.kind == "money":
        doing = f"{action} of {quantity}"       # "approve refunds of $500.01"
    elif len(action.split()) == 1:
        doing = f"{action} {quantity}"          # "upload 6 files", "have 6 active sessions"
    else:
        doing = f"{action} with {quantity}"
    if inside:
        expected = f"The {actor} can {doing}, because it is within the limit ({limit.phrase})"
    else:
        expected = (f"The {actor} cannot {doing}: the request is refused and a message explains "
                    f"the limit ({limit.phrase})")
    return Draft(
        title=text.capitalize(f"{doing}: {'allowed' if inside else 'refused'}"),
        input=text.capitalize(f"{actor}, {quantity}"),
        steps=(f"Log in as {text.with_article(actor)}", ctx.open_step, f"Try to {doing}"),
        expected_output=expected,
    )


def _subject_without_limit(criterion: str, limits: List[Limit]) -> Optional[str]:
    """"Orders over $50 get free shipping" -> "order", not "orders over $50"."""
    subject = text.subject(criterion, singularize=False)
    if not subject:
        return None
    for limit in limits:
        cut = subject.lower().find(limit.phrase.lower())
        if cut < 0:   # a negated limit is reworded ("at most 12"), so look for the number instead
            number = re.search(r"\d", subject)
            words = subject[:number.start()].split() if number else []
            cut = len(" ".join(words[:-1])) if len(words) > 1 and number else -1
        if cut > 0:
            subject = subject[:cut].strip()
    subject = re.sub(r"\s+(?:with|of|for|in|on|at|to|by|that|which|whose)$", "", subject, flags=re.IGNORECASE)
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


# Characters a sample is cut from, so a 7-character password is "Passw0r".
_PASSWORD_CHARS = "Passw0rd!Secure#2026Key"
_DIGIT_CHARS = "1234567890"
_LETTER_CHARS = "abcdefghijklmnopqrstuvwxyz"
_LONGEST_LITERAL = 30


def _length_sample(limit: Limit, subject: str, value: Decimal) -> Optional[str]:
    """A literal value with exactly ``value`` characters: '"Passw0r"' for 7 characters."""
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
                       criterion: str) -> str:
    if condition:
        if inside:
            return f"The rule applies: {text.rule(criterion)}"
        return f"The rule does not apply, because {quantity} is outside the condition '{limit.phrase}'"
    if limit.kind == "length":
        if inside:
            return (f"The {subject} is accepted because {quantity} is within the limit ({limit.phrase}), "
                    "the form is submitted and a success message is shown")
        return (f"The {subject} is rejected, the form is not submitted and an error message "
                f"explains the limit ({limit.phrase})")
    if inside:
        return f"The {subject} is accepted because {quantity} is within the limit ({limit.phrase})"
    return f"The {subject} is rejected and an error message explains the limit ({limit.phrase})"


def _boundary_without_number(ctx: StoryContext, criterion: str) -> List[Draft]:
    subject = text.subject(criterion) or "value"
    statement = text.rule(criterion)
    return [
        Draft(
            title=text.capitalize(f"{subject} exactly at the limit is accepted"),
            input=text.capitalize(f"{subject}: exactly at the limit"),
            steps=(ctx.open_step, f"Use the largest (or smallest) {subject} the rule allows", "Check the result"),
            expected_output=f"The {subject} is accepted because it respects the rule: {statement}",
        ),
        Draft(
            title=text.capitalize(f"{subject} just past the limit is rejected"),
            input=text.capitalize(f"{subject}: one step past the limit"),
            steps=(ctx.open_step, f"Use {text.with_article(subject)} one step past what the rule allows",
                   "Check the result"),
            expected_output=f"The {subject} is rejected and an error message explains the rule: {statement}",
        ),
    ]


# --- security: an allowed user and a blocked user ---------------------------------

@dataclass(frozen=True)
class _Roles:
    allowed: str
    blocked: str
    allowed_account: str
    blocked_account: Optional[str]   # None for an anonymous visitor


_ONLY_GROUP_RE = re.compile(
    r"\bonly\s+(?:the\s+|an?\s+)?(?P<group>[a-z]+(?:\s+[a-z]+)?)\s+(?:can|may|is|are|should|must|have|has)\b",
    re.IGNORECASE,
)
_PROTECTION_RE = re.compile(r"\b(?:encrypt\w*|hash\w*|https|tls|ssl|plain\s*text)\b", re.IGNORECASE)
_ANONYMOUS = "anonymous visitor (not logged in)"


_ACCESS_RE = re.compile(
    r"\b(?:only|admin\w*|owners?|permission\w*|access\w*|authori[sz]\w*|authenticat\w*|logged[\s-]in"
    r"|log\s*in|sign\s*in|roles?|cannot|can't|must\s+not|may\s+not|allowed|forbidden|restricted)\b",
    re.IGNORECASE,
)


def security(ctx: StoryContext, criterion: str) -> List[Draft]:
    if _PROTECTION_RE.search(criterion) and not _ACCESS_RE.search(criterion):
        return _data_protection(ctx, criterion)
    denied = _denied_group(criterion)
    if denied:
        return _denied_group_drafts(ctx, *denied)
    others = _OTHER_USERS_RE.search(criterion)
    refused = _DENIED_ACTION_RE.search(text.sentence(criterion))
    if others and refused:
        return _other_users_drafts(ctx, refused["action"].strip())
    roles = _roles(criterion)
    action = text.criterion_action(criterion) or (refused["action"].strip() if refused else ctx.task)
    drafts = [
        Draft(
            title=text.capitalize(f"{roles.allowed} can {action}"),
            input=_user_input(roles.allowed, roles.allowed_account),
            steps=(_login_step(roles.allowed, roles.allowed_account), ctx.open_step, f"Try to {action}"),
            expected_output=f"Access is granted and the user can {action}",
        ),
        Draft(
            title=text.capitalize(f"{roles.blocked} cannot {action}"),
            input=_user_input(roles.blocked, roles.blocked_account),
            steps=(_login_step(roles.blocked, roles.blocked_account), ctx.open_step, f"Try to {action}"),
            expected_output=("Access is denied (error page, HTTP 403 or redirect to login), the action is not "
                      "performed and no protected data is shown"),
        ),
    ]
    if _PROTECTION_RE.search(criterion):
        drafts.append(Draft(
            title="Sensitive data is never stored or sent in plain text",
            input=f'{_user_input(roles.allowed, roles.allowed_account)}, password "Str0ng!Pass"',
            steps=(_login_step(roles.allowed, roles.allowed_account), f"{text.capitalize(action)}",
                   "Inspect the network traffic and the stored data"),
            expected_output="Traffic uses HTTPS and the sensitive data is stored only in encrypted or hashed form",
        ))
    return drafts


_PREPOSITIONS = {"with", "without", "of", "for", "from", "in", "on", "at", "by", "to", "that", "who", "which"}
_OTHER_USERS_RE = re.compile(r"\b(?:other|another)\s+(?:users?|customers?|members?|people)(?:'s?|’s?)?", re.IGNORECASE)


def _other_users_drafts(ctx: StoryContext, action: str) -> List[Draft]:
    """ "Users cannot delete other users' orders": the owner can, a different user cannot."""
    own = re.sub(r"\b(?:that|which)\s+belongs?\s+to\s+(?:other|another)\s+\w+", "of their own", action,
                 flags=re.IGNORECASE)
    own = _OTHER_USERS_RE.sub("their own", own)
    return [
        Draft(
            title=text.capitalize(f"user can {own}"),
            input=_user_input("owner of the data", "owner@example.com"),
            steps=(_login_step("owner of the data", "owner@example.com"), ctx.open_step, f"Try to {own}"),
            expected_output=f"The action succeeds: the user can {own}",
        ),
        Draft(
            title=text.capitalize(f"user cannot {action}"),
            input=_user_input("different logged-in user", "other.user@example.com"),
            steps=(_login_step("different logged-in user", "other.user@example.com"), ctx.open_step,
                   f"Try to {action}"),
            expected_output=("Access is denied (error page, HTTP 403 or redirect to login), the action is not "
                             "performed and the other user's data is not shown or changed"),
        ),
    ]


def _denied_group(criterion: str) -> Optional[Tuple[str, str, str]]:
    """ "Deactivated users cannot log in" -> ("deactivated user", "user who is not deactivated", "log in")."""
    statement = text.sentence(criterion)
    match = _DENIED_ACTION_RE.search(statement)
    actor = text.subject(statement)
    if not match or not actor or not _PERSON_RE.search(actor) or actor.lower().startswith("only"):
        return None
    without = re.match(r"^(?P<who>\w+)\s+(?:without|with\s+no)\s+(?P<what>.+)$", actor, re.IGNORECASE)
    if without:   # "users without permission" -> "user with permission"
        who = text.singular(without["who"])
        return f"{who} without {without['what']}", f"{who} with {without['what']}", match["action"].strip()
    words = actor.split()
    if len(words) < 2 or not _PERSON_RE.fullmatch(words[-1]) or any(w.lower() in _PREPOSITIONS for w in words):
        return None   # "Users cannot ..." names no group to compare with
    allowed = f"{words[-1]} who is not {' '.join(words[:-1])}"
    return actor, allowed, match["action"].strip()


def _denied_group_drafts(ctx: StoryContext, blocked: str, allowed: str, action: str) -> List[Draft]:
    blocked_account = re.sub(r"[^a-z]+", ".", blocked.lower()).strip(".") + "@example.com"
    return [
        Draft(
            title=text.capitalize(f"{allowed} can {action}"),
            input=_user_input(allowed, "active.user@example.com"),
            steps=(_login_step(allowed, "active.user@example.com") if not action.lower().startswith("log in")
                   else ctx.open_step, f"Try to {action} as {text.with_article(allowed)} (active.user@example.com)"),
            expected_output=f"The action succeeds: the user can {action}",
        ),
        Draft(
            title=text.capitalize(f"{blocked} cannot {action}"),
            input=_user_input(blocked, blocked_account),
            steps=(ctx.open_step, f"Try to {action} as {text.with_article(blocked)} ({blocked_account})"),
            expected_output=(f"The action is refused with a clear message, the {blocked} cannot {action} "
                             "and no protected data is shown"),
        ),
    ]


def _data_protection(ctx: StoryContext, criterion: str) -> List[Draft]:
    """ "Passwords are stored hashed": check storage and transport, not who may log in."""
    data = text.subject(criterion) or "sensitive data"
    return [
        Draft(
            title=text.capitalize(f"{data} is never stored in plain text"),
            input=f'{text.capitalize(data)}: "Str0ng!Pass"',
            steps=(ctx.open_step, f'Save a record with the {data} "Str0ng!Pass"',
                   "Inspect the stored record in the database"),
            expected_output=(f"The stored {data} is not \"Str0ng!Pass\": only its hashed or encrypted form "
                             f"is stored, as required ({text.rule(criterion)})"),
        ),
        Draft(
            title=text.capitalize(f"{data} never appears in traffic, logs or responses"),
            input=f'{text.capitalize(data)}: "Str0ng!Pass"',
            steps=(ctx.open_step, f'Submit the {data} "Str0ng!Pass"',
                   "Inspect the network traffic, the application logs and the API responses"),
            expected_output=f"Traffic uses HTTPS and the {data} \"Str0ng!Pass\" does not appear anywhere in plain text",
        ),
    ]


def _roles(criterion: str) -> _Roles:
    lowered = criterion.lower()
    if re.search(r"\badmin(?:istrator)?s?\b", lowered):
        return _Roles("administrator", "regular user (not an administrator)",
                      "admin@example.com", "user@example.com")
    if re.search(r"\bowners?\b|\btheir own\b|\bhis own\b|\bher own\b", lowered):
        return _Roles("owner of the data", "different logged-in user",
                      "owner@example.com", "other.user@example.com")
    only = _ONLY_GROUP_RE.search(criterion)
    if only and re.search(r"\b(?:authenticated|logged[\s-]in|signed[\s-]in|registered)\b", only["group"], re.IGNORECASE):
        return _Roles("logged-in user", _ANONYMOUS, "user@example.com", None)
    if only:
        group = only["group"].lower()
        return _Roles(f"user in the '{group}' group", f"user outside the '{group}' group",
                      f"{re.sub(r'[^a-z]+', '.', group)}.member@example.com", "outsider@example.com")
    if re.search(r"\blogged[\s-]in\b|\bauthenticated\b|\bsigned[\s-]in\b|\blog\s*in\b|\bsign\s*in\b"
                 r"|\bguests?\b|\banonymous\b|\bvisitors?\b", lowered):
        return _Roles("logged-in user", _ANONYMOUS, "user@example.com", None)
    return _Roles("authorized user", "unauthorized user",
                  "authorized.user@example.com", "unauthorized.user@example.com")


def _user_input(role: str, account: Optional[str]) -> str:
    return f"User: {role} ({account})" if account else f"User: {role}"


def _login_step(role: str, account: Optional[str]) -> str:
    if account is None:
        return "Make sure no user is logged in"
    return f"Log in as {text.with_article(role)} ({account})"


# --- performance: one user, then under load ---------------------------------------

_LOAD_UNIT_RE = re.compile(r"\b(?:users?|requests?|sessions?|connections?|visitors?)\b", re.IGNORECASE)


def performance(ctx: StoryContext, criterion: str) -> List[Draft]:
    limits = extract_limits(criterion)
    time_limit = next((limit for limit in limits if limit.kind == "time"), None)
    load_limit = next((limit for limit in limits if _LOAD_UNIT_RE.search(limit.unit)), None)
    subject = text.subject(criterion) or ctx.feature_name
    load = load_limit.format(load_limit.high or load_limit.low) if load_limit else "100 concurrent users"
    statement = text.rule(criterion)

    if time_limit:
        single_expected = f"Every measurement is {time_limit.phrase}"
        load_expected = f"95% of requests are {time_limit.phrase} and no request fails"
    else:
        single_expected = f"The requirement holds: {statement}"
        load_expected = f"The requirement still holds under load ({statement}) and no request fails"

    return [
        Draft(
            title=text.capitalize(f"{subject} {text.agree(subject, 'meets', 'meet')} the target with a single user"),
            input="1 user, 10 requests in a row",
            steps=(ctx.open_step, "Measure the response time with 1 user, 10 times in a row",
                   "Record the average and the slowest time"),
            expected_output=single_expected,
        ),
        Draft(
            title=text.capitalize(f"{subject} {text.agree(subject, 'meets', 'meet')} the target under load ({load})"),
            input=f"{load} for 5 minutes",
            steps=(f"Prepare a load test (for example with JMeter or Locust) for the {ctx.feature_name} page",
                   f"Simulate {load} for 5 minutes",
                   "Record the 95th-percentile response time and the error rate"),
            expected_output=load_expected,
        ),
    ]


# --- usability: a first-time user, plus one ease-of-use check ---------------------

_MOBILE_RE = re.compile(r"\b(?:mobile|phone|tablet|responsive|small\s+screens?|screen\s+sizes?)\b", re.IGNORECASE)
_MESSAGE_RE = re.compile(r"\b(?:error|message|messages|feedback|confirm\w*|notification\w*|hint)\b", re.IGNORECASE)


def usability(ctx: StoryContext, criterion: str) -> List[Draft]:
    statement = text.rule(criterion)
    drafts = [Draft(
        title=f"First-time user can {ctx.task} without help",
        input="A first-time user, no instructions",
        steps=(f"Give a first-time user this task: {ctx.task}", "Give no instructions or help",
               "Observe where the user hesitates or makes mistakes"),
        expected_output=f"The user completes the task without help, and this holds: {statement}",
    )]
    if _MOBILE_RE.search(criterion):
        drafts.append(Draft(
            title="Page works on a phone-sized screen",
            input="Screen width: 360 px",
            steps=(f"{ctx.open_step} on a screen 360 px wide", f"Try to {ctx.task}",
                   "Check the text, buttons and layout"),
            expected_output="All content fits the screen without sideways scrolling and every button is easy to tap",
        ))
    elif _MESSAGE_RE.search(criterion):
        drafts.append(Draft(
            title="Messages are clear and helpful",
            input="One successful and one failed attempt",
            steps=(ctx.open_step, "Cause one successful and one failed attempt", "Read the messages shown"),
            expected_output="Each message says in plain words what happened and what to do next",
        ))
    else:
        drafts.append(Draft(
            title="Task can be completed with the keyboard only",
            input="Keyboard only: Tab, Shift+Tab, Enter and Space",
            steps=(ctx.open_step, f"Try to {ctx.task} using only Tab, Shift+Tab, Enter and Space",
                   "Watch the focus indicator"),
            expected_output=("Every control can be reached and used with the keyboard "
                             "and the focused element is always visible"),
        ))
    return drafts


# --- criterion shapes that need their own cases, whatever the predicted category --------

_EMPTY_INPUT_RE = re.compile(
    r"^(?:an?\s+|the\s+)?(?:empty|blank)\s+(?P<thing>[a-z]+(?:\s+[a-z]+)??)\s+"
    r"(?:(?:must|should|will|shall)\s+)?(?:shows?|displays?)\b",
    re.IGNORECASE,
)
_RESULTS_MATCH_RE = re.compile(
    r"\b(?:search\s+)?results?\s+(?:(?:must|should|will|shall)\s+)?(?:only\s+)?"
    r"(?:match|contain|include)\w*\s+(?:the\s+)?(?:entered|searched|typed|given)\s+(?P<term>[a-z]+(?:\s+[a-z]+)?)",
    re.IGNORECASE,
)
_WRONG_SECRET_RE = re.compile(
    r"\b(?:incorrect|wrong)\s+(?P<what>passwords?|credentials|pins?|codes?|otps?|verification\s+codes?)\b"
    r"|\binvalid\s+(?P<login>credentials|login\s+details)\b",
    re.IGNORECASE,
)
_SHAPED_CATEGORIES = {"functional", "validation", "security"}


def shaped(ctx: StoryContext, criterion: str, category: str) -> List[Draft]:
    """Cases for criteria whose meaning the category templates would get wrong.

    "Incorrect passwords must be rejected" is about a password that does not match the account,
    not its format; "An empty search must show a message" is about leaving the input empty;
    "Search results must match the entered name" is about the results, not an input to validate.
    Returns [] when no shape fits, so the category template is used.
    """
    if category not in _SHAPED_CATEGORIES:
        return []
    statement = text.sentence(criterion)
    wrong = _WRONG_SECRET_RE.search(statement)
    if wrong:
        return _wrong_secret_drafts(ctx, (wrong["what"] or wrong["login"]).lower())
    if category == "security":
        return []
    empty = _EMPTY_INPUT_RE.search(statement)
    if empty:
        return _empty_input_drafts(ctx, statement, empty["thing"].lower())
    match = _RESULTS_MATCH_RE.search(statement)
    if match:
        return _results_match_drafts(ctx, match["term"].lower())
    return []


def _wrong_secret_drafts(ctx: StoryContext, what: str) -> List[Draft]:
    email = "registered.user@example.com"
    if re.match(r"pin|code|otp|verification", what):
        label = "verification code" if what.startswith(("otp", "verification")) else text.singular(what)
        return [
            Draft(title=f"Correct {label} is accepted", input=f'{text.capitalize(label)}: "482913" (the one sent)',
                  steps=(ctx.open_step, f'Enter the {label} "482913"', "Submit"),
                  expected_output=f"The {label} is accepted and the action is completed"),
            Draft(title=f"Incorrect {label} is rejected", input=f'{text.capitalize(label)}: "482914" (one digit wrong)',
                  steps=(ctx.open_step, f'Enter the {label} "482914"', "Submit"),
                  expected_output=f"The {label} is refused, a clear error is shown and the action is not completed"),
        ]
    refused = ("Login is refused with a general error that does not say whether the email or the password "
               "was wrong, and the user stays logged out")
    account = f'Email: "{email}" (its password is "Str0ng!Pass")'
    return [
        Draft(title="Correct password for a registered account is accepted",
              input=f'{account}, password entered: "Str0ng!Pass"',
              steps=(ctx.open_step, f'Enter "{email}" and the password "Str0ng!Pass"', "Submit the form"),
              expected_output="The user is logged in"),
        Draft(title="Incorrect password for a registered account is rejected",
              input=f'{account}, password entered: "Wr0ng!Pass"',
              steps=(ctx.open_step, f'Enter "{email}" and the password "Wr0ng!Pass"', "Submit the form"),
              expected_output=refused),
        Draft(title="Password in the wrong letter case is rejected",
              input=f'{account}, password entered: "str0ng!pass"',
              steps=(ctx.open_step, f'Enter "{email}" and the password "str0ng!pass"', "Submit the form"),
              expected_output=refused),
    ]


def _empty_input_drafts(ctx: StoryContext, statement: str, thing: str) -> List[Draft]:
    """ "An empty search must show a helpful message": empty, spaces only, and real text."""
    submit = "Run the search" if "search" in thing else "Submit the form"
    field = "search box" if thing == "search" else f"{thing} field"
    shown = re.search(r"\b(?:shows?|displays?)\s+(?P<what>.+)$", text.affirm(text.outcome(statement)), re.IGNORECASE)
    what = shown["what"].rstrip(".") if shown else "a message"
    message = f"{text.capitalize(what)} is shown"
    short = thing.split()[-1]
    return [
        Draft(title=text.capitalize(f"empty {thing} shows {what}"),
              input=f"{text.capitalize(field)}: (empty)",
              steps=(ctx.open_step, f"Leave the {field} empty", submit),
              expected_output=f"{message}; the page does not crash or show an error page"),
        Draft(title=text.capitalize(f"{thing} of spaces only is treated as empty"),
              input=f'{text.capitalize(field)}: "   " (spaces only)',
              steps=(ctx.open_step, f"Type three spaces in the {field}", submit),
              expected_output=f"The same as an empty {thing}: {text.lower_first(message)}"),
        Draft(title=text.capitalize(f"{thing} with text does not show the empty-{short} message"),
              input=(f"{text.capitalize(field)}: a word that matches at least one item" if "search" in thing
                     else f'{text.capitalize(field)}: "Looks good to me"'),
              steps=(ctx.open_step, (f"Type a word that matches at least one item in the {field}" if "search" in thing
                                     else f'Type "Looks good to me" in the {field}'), submit),
              expected_output=(f"Matching results are shown and the empty-{short} message is not shown"
                               if "search" in thing
                               else f"The {thing} is accepted and the empty-{short} message is not shown")),
    ]


def _results_match_drafts(ctx: StoryContext, term: str) -> List[Draft]:
    return [
        Draft(title=text.capitalize(f"existing {term} returns the matching item"),
              input=f"Search: the {term} of an item that exists, typed in full",
              steps=(ctx.open_step, f"Type the {term} of an existing item in the search box", "Run the search"),
              expected_output=f"That item is listed and every result matches the entered {term}"),
        Draft(title=text.capitalize(f"{term} that matches nothing returns no results"),
              input=f'Search: "zzqxw" (no item has this {term})',
              steps=(ctx.open_step, 'Type "zzqxw" in the search box', "Run the search"),
              expected_output="No items are listed, a \"no results\" message is shown and no unrelated items appear"),
    ]


TEMPLATES: Dict[str, Template] = {
    "functional": functional,
    "validation": validation,
    "boundary": boundary,
    "security": security,
    "performance": performance,
    "usability": usability,
}
