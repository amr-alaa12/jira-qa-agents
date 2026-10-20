"""Find numeric limits in acceptance criteria.

"The new password must be at least 8 characters" contains the limit
"at least 8 characters". Boundary tests then probe the values just below,
at and just above that limit: 7, 8 and 9 characters.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional, Tuple

# How a limit relates to its number.
MIN = "min"                      # at least 8          -> 8 is allowed
MAX = "max"                      # at most 64          -> 64 is allowed
MIN_EXCLUSIVE = "min_exclusive"  # more than 50        -> 50 is not allowed
MAX_EXCLUSIVE = "max_exclusive"  # under 2 seconds     -> 2 is not allowed
EXACT = "exact"                  # exactly 4 digits
TRIGGER = "trigger"              # after 3 attempts    -> something happens at 3
RANGE = "range"                  # between 8 and 20

LENGTH_UNITS = {"character", "characters", "char", "chars", "letter", "letters",
                "digit", "digits", "symbol", "symbols", "word", "words"}
TIME_UNITS = {"ms", "millisecond", "milliseconds", "second", "seconds", "sec", "secs",
              "minute", "minutes", "min", "mins", "hour", "hours", "hr", "hrs",
              "day", "days", "week", "weeks", "month", "months", "year", "years"}
SIZE_UNITS = {"byte", "bytes", "kb", "mb", "gb", "tb"}
ATTEMPT_UNITS = {"attempt", "attempts", "try", "tries", "request", "requests", "click", "clicks"}
REPEAT_UNITS = {"time", "times"}
ITEM_UNITS = {"item", "items", "product", "products", "file", "files", "photo", "photos",
              "image", "images", "attachment", "attachments", "entry", "entries",
              "record", "records", "row", "rows", "ticket", "tickets", "seat", "seats"}
_KNOWN_UNITS = LENGTH_UNITS | TIME_UNITS | SIZE_UNITS | ATTEMPT_UNITS | REPEAT_UNITS | ITEM_UNITS

# Words that end a unit: "8 characters long", "10 items in the cart".
_UNIT_STOP_WORDS = {"a", "after", "an", "and", "are", "at", "be", "before", "by", "each",
                    "every", "for", "from", "if", "in", "into", "is", "it", "its", "long",
                    "must", "of", "old", "on", "or", "over", "per", "should", "so", "than",
                    "that", "the", "their", "then", "to", "under", "when", "which", "who",
                    "with", "within", "without"}

_NUMBER_WORDS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                 "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
                 "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
                 "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
                 "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60}
_NUMBER_WORD_RE = re.compile(r"\b(" + "|".join(_NUMBER_WORDS) + r")\b", re.IGNORECASE)

_NUM = r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?"
_CUR = r"[$€£]"

_RANGE_RES = [
    re.compile(rf"\bbetween\s+(?P<cur>{_CUR})?(?P<lo>{_NUM})(?:\s*%|\s+[a-z]+)?\s+and\s+{_CUR}?(?P<hi>{_NUM})",
               re.IGNORECASE),
    re.compile(rf"\bfrom\s+(?P<cur>{_CUR})?(?P<lo>{_NUM})\s+to\s+{_CUR}?(?P<hi>{_NUM})", re.IGNORECASE),
    re.compile(rf"(?<![\w.,$€£])(?P<cur>{_CUR})?(?P<lo>{_NUM})\s*(?:-|–|to)\s*{_CUR}?(?P<hi>{_NUM})(?!\d)",
               re.IGNORECASE),
]
_SINGLE_RE = re.compile(rf"(?<![\w.,])(?P<cur>{_CUR}\s?)?(?P<num>{_NUM})(?!\d)")

# Qualifiers written before the number. Longer phrases come first in each
# group; the regex is anchored to the end of the text before the number.
_PREFIX_PATTERNS = [
    (MAX, r"(?:not|never)\s+exceed(?:s|ing)?|no\s+more\s+than|not\s+more\s+than|no\s+longer\s+than"
          r"|at\s+most|a\s+maximum\s+of|maximum\s+of|maximum|max\.?|up\s+to|limited\s+to|within"),
    (MIN, r"no\s+less\s+than|not\s+less\s+than|no\s+fewer\s+than|no\s+shorter\s+than|at\s+least"
          r"|a\s+minimum\s+of|minimum\s+of|minimum|min\.?"),
    (MIN_EXCLUSIVE, r"more\s+than|greater\s+than|longer\s+than|higher\s+than|exceed(?:s|ing)?"
                    r"|over|above|beyond"),
    (MAX_EXCLUSIVE, r"less\s+than|fewer\s+than|shorter\s+than|lower\s+than|under|below"),
    (EXACT, r"exactly|equal\s+to|equals"),
    (TRIGGER, r"after|once|reaches|reaching"),
]
_PREFIX_RE = re.compile(
    r"\b(?:" + "|".join(f"(?P<{relation}>{pattern})" for relation, pattern in _PREFIX_PATTERNS)
    + r")\s*$",
    re.IGNORECASE,
)
# Qualifiers written after the number or unit: "8 or more characters".
_POSTFIX_RE = re.compile(
    r"\s*(?:or|and)\s+(?:(?P<min>more|greater|longer|above|higher|over|up)"
    r"|(?P<max>less|fewer|shorter|below|lower|under))\b",
    re.IGNORECASE,
)
_PERCENT_RE = re.compile(r"\s?%")
_FIRST_WORD_RE = re.compile(r"\s*([A-Za-z][A-Za-z-]*)")
_NEXT_WORD_RE = re.compile(r"\s+([A-Za-z][A-Za-z-]*)")


@dataclass(frozen=True)
class Limit:
    """One numeric limit found in a criterion."""

    relation: str
    low: Decimal                 # the number (the lower number for a range)
    high: Optional[Decimal]      # the upper number, only for a range
    unit: str                    # "characters", "failed login attempts", "%", "" ...
    currency: str                # "$", "€", "£" or ""
    step: Decimal                # smallest meaningful change: 1, 0.1, 0.01 ...
    phrase: str                  # readable limit, e.g. "at least 8 characters"
    position: int                # where the limit starts in the criterion

    @property
    def kind(self) -> str:
        """The kind of quantity: length, time, size, attempts, repeat, items, money, percent, other."""
        if self.currency:
            return "money"
        if self.unit == "%":
            return "percent"
        last_word = self.unit.split()[-1].lower() if self.unit else ""
        for kind, units in (("length", LENGTH_UNITS), ("time", TIME_UNITS), ("size", SIZE_UNITS),
                            ("attempts", ATTEMPT_UNITS), ("repeat", REPEAT_UNITS),
                            ("items", ITEM_UNITS)):
            if last_word in units:
                return kind
        return "other"

    def probes(self) -> List[Tuple[Decimal, bool]]:
        """Values to test, each paired with True when it is inside the limit."""
        v, s = self.low, self.step
        probes: List[Tuple[Decimal, bool]]
        if self.relation == RANGE and self.high is not None:
            probes = [(v - s, False), (v, True), (self.high, True), (self.high + s, False)]
        else:
            inside = {
                MIN: (False, True, True),
                TRIGGER: (False, True, True),
                MAX: (True, True, False),
                MIN_EXCLUSIVE: (False, False, True),
                MAX_EXCLUSIVE: (True, False, False),
                EXACT: (False, True, False),
            }[self.relation]
            probes = list(zip((v - s, v, v + s), inside))
        if self.low >= 0:
            probes = [(value, ok) for value, ok in probes if value >= 0]
        return probes

    def format(self, value: Decimal) -> str:
        """Write a value with its unit: "7 characters", "$49.99", "80%", "1 second"."""
        if self.currency:
            number = f"{value:.2f}" if value != value.to_integral_value() else f"{value:.0f}"
            return f"{self.currency}{number}"
        number = format(value.normalize(), "f")
        if self.unit == "%":
            return f"{number}%"
        if not self.unit:
            return number
        unit = _singular(self.unit) if value == 1 else self.unit
        return f"{number} {unit}"


def extract_limits(criterion: str) -> List[Limit]:
    """Return every numeric limit in a criterion, in reading order."""
    text = _NUMBER_WORD_RE.sub(lambda m: str(_NUMBER_WORDS[m.group(1).lower()]), criterion)
    limits: List[Limit] = []
    taken: List[Tuple[int, int]] = []

    for regex in _RANGE_RES:
        for match in regex.finditer(text):
            if _overlaps(taken, match.start(), match.end()):
                continue
            low, high = _to_decimal(match["lo"]), _to_decimal(match["hi"])
            if low >= high:
                continue
            currency = match["cur"] or ""
            unit, end = _read_unit(text, match.end())
            step = min(_step(match["lo"], currency), _step(match["hi"], currency))
            limits.append(Limit(RANGE, low, high, unit, currency, step,
                                text[match.start():end].strip(), match.start()))
            taken.append((match.start(), end))

    for match in _SINGLE_RE.finditer(text):
        if _overlaps(taken, match.start(), match.end()):
            continue
        currency = (match["cur"] or "").strip()
        relation, end = _read_postfix(text, match.end())
        # A currency is the unit already: "$50 get free shipping" has no unit words.
        unit, end = ("", end) if currency else _read_unit(text, end)
        if relation is None:
            relation, end = _read_postfix(text, end)

        start = match.start()
        prefix = _PREFIX_RE.search(text[:start])
        if prefix:
            relation = prefix.lastgroup
            start = prefix.start()
        phrase = text[start:end].strip()
        if prefix and re.match(r"(?:not|never)\s+exceed", prefix.group(0), re.IGNORECASE):
            phrase = "at most " + text[match.start():end].strip()

        value = _to_decimal(match["num"])
        unit = _plural(unit)
        limit = Limit(relation or EXACT, value, None, unit, currency,
                      _step(match["num"], currency), phrase, start)
        if relation is None and limit.kind == "time":
            # "loads in 2 seconds" states a deadline, so read it as "within".
            limit = Limit(MAX, value, None, unit, currency, limit.step, f"within {phrase}", start)
        limits.append(limit)
        taken.append((match.start(), end))

    return sorted(limits, key=lambda limit: limit.position)


def _read_postfix(text: str, pos: int) -> Tuple[Optional[str], int]:
    match = _POSTFIX_RE.match(text, pos)
    if not match:
        return None, pos
    return (MIN if match["min"] else MAX), match.end()


def _read_unit(text: str, pos: int) -> Tuple[str, int]:
    """Read up to three unit words after a number: "3 failed login attempts"."""
    percent = _PERCENT_RE.match(text, pos)
    if percent:
        return "%", percent.end()
    words: List[str] = []
    end = pos
    while len(words) < 3:
        match = (_NEXT_WORD_RE if words else _FIRST_WORD_RE).match(text, end)
        if not match or match.group(1).lower() in _UNIT_STOP_WORDS:
            break
        words.append(match.group(1))
        end = match.end()
        if match.group(1).lower() in _KNOWN_UNITS:
            break
    return " ".join(words), end


def _to_decimal(raw: str) -> Decimal:
    return Decimal(raw.replace(",", ""))


def _step(raw: str, currency: str) -> Decimal:
    if currency:
        return Decimal("0.01")
    decimals = raw.split(".")[1] if "." in raw else ""
    return Decimal(1).scaleb(-len(decimals))


def _overlaps(taken: List[Tuple[int, int]], start: int, end: int) -> bool:
    return any(start < taken_end and taken_start < end for taken_start, taken_end in taken)


def _plural(unit: str) -> str:
    """Store units in plural form ("at least one item" -> "items") so "2 items" reads right."""
    if not unit:
        return unit
    words = unit.split()
    last = words[-1]
    plural = last[:-1] + "ies" if last.lower().endswith(("ry", "ty")) else last + "s"
    if plural.lower() in _KNOWN_UNITS:
        words[-1] = plural
    return " ".join(words)


def _singular(unit: str) -> str:
    words = unit.split()
    last = words[-1]
    if last.lower() == "entries":
        last = last[:-3] + "y"
    elif last.lower() == "tries":
        last = last[:-3] + "y"
    elif last.endswith("s") and not last.endswith("ss") and len(last) > 2:
        last = last[:-1]
    return " ".join(words[:-1] + [last])
