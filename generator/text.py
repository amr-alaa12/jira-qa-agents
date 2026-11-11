"""Small helpers that pull readable phrases out of stories and criteria."""

from __future__ import annotations

import re
from typing import Optional

# An auxiliary is the safest place to split subject and predicate, so it is tried first:
# "The display name cannot be ..." must not split at "display".
_SUBJECT_AUX_RE = re.compile(
    r"^(?P<subject>(?:(?:the|a|an)\s+)?\S+(?:\s+\S+)*?)\s+(?:must|should|shall|cannot|can't|can|will|may"
    r"|has\s+to|have\s+to|needs?\s+to|is|are)\b",
    re.IGNORECASE,
)
_SUBJECT_VERB_RE = re.compile(
    r"^(?P<subject>(?:(?:[Tt]he|[Aa]n?)\s+)?\S+(?:\s+\S+)*?)\s+"
    r"(?:gets?|receives?|loads?|returns?|responds?|opens?|appears?|displays?|shows?"
    r"|accepts?|allows?|supports?|stores?|sends?|contains?|lists?|keeps?|stays?|remains?)\b",
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
_THEN_RE = re.compile(r"\bthen\s+(?P<outcome>.+)$", re.IGNORECASE)
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


_GWT_START_RE = re.compile(r"^\s*(?:given|when)\b", re.IGNORECASE)


def subject(criterion: str, singularize: bool = True) -> Optional[str]:
    """The thing a criterion talks about: "The new password must ..." -> "new password".

    For "Given ..., when ..., then X ..." and "After ..., X ..." the subject comes from X.
    """
    statement = sentence(about_user(criterion))
    if _GWT_START_RE.match(statement):
        statement = re.sub(r"^given\s+", "", sentence(outcome(statement)), flags=re.IGNORECASE)
    leading = re.match(r"^(?:after|once|when|whenever|if|upon|before|while)\b[^,]+,\s*(?P<main>.+)$",
                       statement, re.IGNORECASE)
    if leading:
        statement = leading["main"]
    statement = re.sub(r"^only\s+", "", statement, flags=re.IGNORECASE)
    match = _SUBJECT_AUX_RE.match(statement) or _SUBJECT_VERB_RE.match(statement)
    if not match:
        return None
    found = lower_first(strip_article(match["subject"].strip()))
    found = re.sub(r"\s+(?:field|input|box)$", "", found, flags=re.IGNORECASE)   # "country field" -> "country"
    if not found or len(found.split()) > 5 or "," in found:
        return None
    return singular(found) if singularize else found


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


def outcome(criterion: str) -> str:
    """The expected result: "Given ..., when ..., then the page is shown" -> "the page is shown"."""
    statement = sentence(criterion)
    match = _THEN_RE.search(statement)
    return match["outcome"].strip() if match else statement


# --- turning an expected outcome into a positive or a negative assertion ------------
#
# Acceptance criteria state outcomes as requirements ("the review should be saved
# successfully"). A test case states what is observed: the positive case needs
# "the review is saved successfully" and a negative case needs the logical opposite,
# "the review is not saved" -- never the requirement pasted after "this does not happen".

_MODAL = (r"should|must|shall|will|would|needs?\s+to|has\s+to|have\s+to"
          r"|(?:is|are)\s+(?:expected|required|supposed)\s+to")
_CLAUSE_RE = re.compile(
    rf"^(?P<subject>.+?)\s+(?:(?P<modal>{_MODAL})(?P<neg>\s+(?:not|never))?"
    r"|(?P<can>can(?:not|'t)?|could)"
    r"|(?P<be>is|are|am|was|were))\s+(?P<rest>.+)$",
    re.IGNORECASE,
)
# Present-tense verbs criteria use without an auxiliary: "The user receives a link".
_VERB_FORMS = {
    "gets": "get", "receives": "receive", "sees": "see", "loads": "load", "returns": "return",
    "responds": "respond", "opens": "open", "appears": "appear", "displays": "display",
    "shows": "show", "sends": "send", "creates": "create", "saves": "save", "stores": "store",
    "redirects": "redirect", "becomes": "become", "contains": "contain", "includes": "include",
    "lists": "list", "updates": "update", "deletes": "delete", "removes": "remove",
    "adds": "add", "stays": "stay", "remains": "remain", "goes": "go", "has": "have",
    "notifies": "notify", "logs": "log", "navigates": "navigate", "starts": "start",
    "completes": "complete", "confirms": "confirm", "accepts": "accept", "allows": "allow",
}
_BASE_FORMS = set(_VERB_FORMS.values())
# Lower case only: a capitalised word is a UI label ("clicks Save"), not the main verb.
_VERB_WORD_RE = re.compile(
    rf"\b(?:{'|'.join(sorted(set(_VERB_FORMS) | _BASE_FORMS, key=len, reverse=True))})\b")
# A leading time/condition clause is context, not part of the outcome: "After the user clicks Save, ...".
_LEADING_CLAUSE_RE = re.compile(
    r"^(?P<clause>(?:after|once|when|whenever|if|upon|as\s+soon\s+as|before|while|on)\b[^,]+),\s*(?P<main>.+)$",
    re.IGNORECASE,
)
_NEGATIVE_WORD_RE = re.compile(r"^(?:not|never|no|none|nothing|nobody|neither)\b", re.IGNORECASE)
# A subject that already negates the outcome: "no automatic reply is sent".
_NEGATIVE_SUBJECT_RE = re.compile(r"^(?:no|none|nothing|nobody|no\s+one|neither)\b", re.IGNORECASE)
# An outcome that is itself an error path: its negative case must not be "negated" into a success.
_FAILURE_OUTCOME_RE = re.compile(
    r"\b(?:reject\w*|errors?|invalid|den(?:y|ied|ies)|prevent\w*|block\w*|fail\w*|refus\w*"
    r"|disallow\w*|forbid\w*|unable|not|never|cannot|can't|warning|lock(?:s|ed)?\s+out|locked"
    r"|no|none|nothing|nobody|neither|nor)\b",
    re.IGNORECASE,
)
# Adverbs that make a negated sentence ambiguous: "is not saved successfully".
_SUCCESS_ADVERB_RE = re.compile(r"\s+(?:successfully|correctly|properly|as\s+expected)\b", re.IGNORECASE)
# Second word of a coordinated verb phrase: "... and display THE order summary".
_OBJECT_START = {"the", "a", "an", "my", "your", "his", "her", "its", "our", "their", "me", "him",
                 "them", "us", "it", "this", "that", "these", "those", "all", "each", "every", "any",
                 "to", "from", "with", "in", "on", "at", "for", "by", "of", "back", "up", "out"}
_PRONOUN_SUBJECTS = {"i": ("am", "do"), "we": ("are", "do"), "you": ("are", "do"), "they": ("are", "do")}
_MAX_SUBJECT_WORDS = 6


def is_failure_outcome(statement: str) -> bool:
    """True for outcomes such as "the payment is rejected and an error message is shown"."""
    return bool(_FAILURE_OUTCOME_RE.search(statement))


def affirm(statement: str) -> str:
    """State an outcome as an observation: "the review should be saved" -> "the review is saved"."""
    clause = _LEADING_CLAUSE_RE.match(sentence(statement))
    if clause:
        return f"{lower_first(affirm(clause['main']))} {lower_first(clause['clause'])}"
    parsed = _parse_clause(statement)
    if not parsed:
        return statement
    subject, kind, rest = parsed
    be, _ = _be_do(subject)
    if kind == "modal":
        if rest.lower().startswith("be "):
            return f"{subject} {be} {rest[3:]}"
        return f"{subject} {_verb_phrases(rest, _third_person if be == 'is' else None, ' and ')}"
    if kind == "modal_not":
        if rest.lower().startswith("be "):
            return f"{subject} {be} not {rest[3:]}"
        return f"{subject} {_be_do(subject)[1]} not {rest}"
    return statement


def negate(statement: str) -> Optional[str]:
    """The logical opposite of an outcome, or None when it cannot be stated safely.

    "the review should be saved successfully" -> "the review is not saved"
    "the system should create the order and display the summary"
        -> "the system does not create the order or display the summary"
    "the user receives a reset link by email" -> "the user does not receive a reset link by email"
    "After the user clicks Save, an email is sent" -> "an email is not sent after the user clicks Save"
    """
    clause = _LEADING_CLAUSE_RE.match(sentence(statement))
    if clause:
        negated = negate(clause["main"])
        return f"{negated} {lower_first(clause['clause'])}" if negated else None
    parsed = _parse_clause(statement)
    if not parsed:
        return None
    subject, kind, rest = parsed
    if (kind == "modal_not" or _NEGATIVE_WORD_RE.match(rest) or _NEGATIVE_SUBJECT_RE.match(subject)
            or re.match(r"only\b", subject, re.IGNORECASE)):   # "only admins can X" has no simple opposite
        return None   # the outcome is already negative; flipping it gives a double negative
    rest = _SUCCESS_ADVERB_RE.sub("", rest).strip()
    be, do = _be_do(subject)
    does = "does" if do == "does" else "do"
    if kind == "modal":
        if rest.lower().startswith("be "):
            return f"{subject} {be} not {rest[3:]}"
        return f"{subject} {does} not {_verb_phrases(rest, None, ' or ')}"
    if kind == "can":
        return f"{subject} cannot {_verb_phrases(rest, None, ' or ')}"
    if kind == "be":
        return f"{subject} {_keep_be(statement, subject)} not {rest}"
    if kind == "verb":
        return f"{subject} {does} not {_verb_phrases(rest, None, ' or ')}"
    return None


def precondition(criterion: str) -> Optional[str]:
    """The "Given" part, written about the user: "Given my cart is empty, when ..." -> "the cart is empty"."""
    match = re.match(r"^\s*given\s+(?P<given>.+?)\s*,?\s+when\b", sentence(criterion), re.IGNORECASE)
    if not match:
        return None
    return lower_first(about_user(match["given"].strip()))


_FIRST_PERSON_VERB_RE = re.compile(r"\bI\s+(?P<verb>[a-z]+)\b")
_AUXILIARIES = {"am", "have", "should", "must", "shall", "will", "would", "can", "cannot", "could", "may",
                "need", "do", "did", "was", "had"}


def about_user(statement: str) -> str:
    """Rewrite the story teller's "I/me/my" as "the user", because test cases are read by a tester.

    "no automatic reply is sent to me" -> "no automatic reply is sent to the user"
    "I receive an email" -> "the user receives an email"
    """
    statement = re.sub(r"\bI\s+am\b", "the user is", statement)
    statement = re.sub(r"\bI\s+have\b", "the user has", statement)
    statement = re.sub(r"\bI'm\b", "the user is", statement)

    def third(match):
        verb = match["verb"]
        return f"the user {verb}" if verb in _AUXILIARIES else "the user " + _third_person(verb)
    statement = _FIRST_PERSON_VERB_RE.sub(third, statement)
    statement = re.sub(r"\bI\b", "the user", statement)
    statement = re.sub(r"\bme\b", "the user", statement)
    return re.sub(r"\bmy\b", "the", statement, flags=re.IGNORECASE)


def _parse_clause(statement: str):
    """Split an outcome into (subject, kind, rest); kind is modal, modal_not, can, be or verb."""
    statement = sentence(statement)
    match = _CLAUSE_RE.match(statement)
    if match and "," not in match["subject"] and len(match["subject"].split()) <= _MAX_SUBJECT_WORDS:
        subject, rest = match["subject"].strip(), match["rest"].strip()
        if match["modal"]:
            return subject, ("modal_not" if match["neg"] else "modal"), rest
        if match["can"]:
            if match["can"].lower() in ("cannot", "can't"):
                return subject, "modal_not", rest
            return subject, "can", rest
        return subject, "be", rest
    # No auxiliary: find the main verb, "The status update appears on the page".
    for verb_match in _VERB_WORD_RE.finditer(statement):
        subject = statement[:verb_match.start()].strip()
        if not subject or "," in subject or len(subject.split()) > _MAX_SUBJECT_WORDS:
            continue
        verb = verb_match.group(0).lower()
        if verb in _VERB_FORMS:
            base = _VERB_FORMS[verb]
        elif _be_do(subject)[1] == "do":   # a base form only follows a plural subject: "Orders get"
            base = verb
        else:
            continue
        rest = statement[verb_match.end():].strip()
        return subject, "verb", f"{base} {rest}".strip()
    return None


def _keep_be(statement: str, subject: str) -> str:
    """The form of "to be" the statement already uses: "the page is shown" -> "is"."""
    after = sentence(statement)[len(subject):].strip()
    return after.split(" ", 1)[0].lower()


def _be_do(subject: str):
    word = subject.split()[-1].lower()
    if subject.lower() in _PRONOUN_SUBJECTS:
        return _PRONOUN_SUBJECTS[subject.lower()]
    plural = singular(word) != word or word in ("people", "children", "data")
    return ("are", "do") if plural and word != "data" else ("is", "does")


def _verb_phrases(rest: str, conjugate, joiner: str) -> str:
    """Re-join coordinated verb phrases ("create X and display Y"), conjugating each verb if asked."""
    parts = rest.split(" and ")
    phrases = [parts[0]]
    for part in parts[1:]:
        words = part.split()
        if len(words) >= 2 and words[1].lower() in _OBJECT_START and words[0].isalpha() and words[0].islower():
            phrases.append(part)
        else:
            phrases[-1] = f"{phrases[-1]} and {part}"
    if conjugate:
        phrases = [conjugate(p) for p in phrases]
    return joiner.join(phrases)


def _third_person(phrase: str) -> str:
    """ "create the order" -> "creates the order"."""
    verb, _, tail = phrase.partition(" ")
    lowered = verb.lower()
    if lowered == "have":
        verb = "has"
    elif lowered == "be":
        verb = "is"
    elif re.search(r"[^aeiou]y$", lowered):
        verb = verb[:-1] + "ies"
    elif re.search(r"(?:s|sh|ch|x|z|o)$", lowered):
        verb = verb + "es"
    else:
        verb = verb + "s"
    return f"{verb} {tail}".strip()


def rule(criterion: str) -> str:
    """A criterion as a tester reads it in an expected output.

    The Given/When part becomes the setup, so only the outcome is kept; it is stated as an
    observation and about "the user": "Given I ..., then the review should be saved"
    -> "the review is saved".
    """
    return lower_first(affirm(about_user(outcome(criterion))))


_PERMISSION_RE = re.compile(r"\b(?:can|may|could|(?:is|are)\s+(?:allowed|able)\s+to)\b", re.IGNORECASE)
_ONLY_RE = re.compile(r"^\s*only\b|\bonly\s+(?:the\s+)?\w+\s+(?:can|may|is|are)\b", re.IGNORECASE)


def is_permission(statement: str) -> bool:
    """ "Customers can edit their review" states a right, not a result: a failed form does not revoke it."""
    parsed = _parse_clause(statement)
    return bool(parsed and parsed[1] == "can") or bool(_ONLY_RE.search(statement))


def agree(subject: str, singular_form: str, plural_form: str) -> str:
    """Pick the verb form that matches the subject: "Replies of STOP meet", "The page meets"."""
    head = re.split(r"\s+(?:of|for|in|on|with|from|to)\s+", subject, maxsplit=1)[0]
    return plural_form if _be_do(head)[1] == "do" else singular_form
