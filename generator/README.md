# Test Case Generator (Member 4)

Takes a user story plus the category of each acceptance criterion and writes test cases in the format agreed at kickoff (`examples/test_cases.json`).

**Input → output:** `stories.json` + categories → `test_cases.json`

## Run it

From the repository root:

```bash
pip install -r generator/requirements.txt   # only pytest; the generator itself needs no packages
python generator/generate.py                # examples/stories.json -> generator/test_cases.json
```

Options:

```bash
python generator/generate.py path/to/stories.json \
    --categories generator/categories.json \
    --output generator/test_cases.json
```

Until the AI model is connected, `generator/categories.json` holds the categories typed by hand. It has one list per story key, with one category per acceptance criterion, in the same order:

```json
{ "SHOP-1": ["functional", "boundary"] }
```

On bad input the script prints a clear `Error: ...` message and exits with code 1. Bad input means: a missing file, invalid JSON, a story with no categories, an unknown category, or a different number of categories than criteria.

## Use it from code (for `main.py`)

```python
from generator import generate_test_cases

test_cases = generate_test_cases(story, ["functional", "boundary"])
```

`categories` can also be the `(category, confidence)` pairs that `predict_category()` returns, so the integration is one line:

```python
categories = [predict_category(c) for c in story["acceptance_criteria"]]
test_cases = generate_test_cases(story, categories)
```

`generate_for_stories(stories, {"SHOP-1": [...], ...})` does the same for a list of stories. Ids are `<story key>-TC1`, `-TC2`, … and are numbered separately for each story.

## Templates

Every acceptance criterion produces at least 2 test cases.

| Category | Test cases |
|---|---|
| `functional` | the normal path with valid data, and one failure path with invalid or missing data |
| `validation` | one valid input and two invalid inputs. Sample values depend on the field: email, phone, date, URL, card, postal code, password, number or name. A required field is also tested empty. |
| `boundary` | just below, at and just above every number found with `re`. "at least 8 characters" → 7 (rejected), 8 and 9 (accepted). Ranges ("between 3 and 20") test both ends. Money uses cent steps ($49.99 / $50 / $50.01). Rules such as "locked after 3 attempts" are tested as "applies / does not apply yet". |
| `security` | an allowed user and a blocked user: admin vs regular user, owner vs other user, a named group, or logged-in user vs anonymous visitor. A criterion about encryption or hashing gets a third, data-protection case. |
| `performance` | one measurement with a single user and one load test (100 concurrent users by default, or the number in the criterion). Both use the time limit from the criterion, e.g. "under 2 seconds". |
| `usability` | a first-time user completes the task without help, plus one check: a phone-sized screen, clear messages, or keyboard-only use (depending on the criterion) |

The numbers parser understands `at least`, `at most`, `no more than`, `must not exceed`, `up to`, `within`, `more than`, `over`, `less than`, `under`, `exactly`, `after`, `between X and Y`, `X or more`, decimals, `%`, currencies (`$ € £`) and number words (`one` … `twenty`).

## Files

| File | Purpose |
|---|---|
| `core.py` | `generate_test_cases()` and `generate_for_stories()`, input checks |
| `templates.py` | one template per category |
| `limits.py` | finds numeric limits ("at least 8 characters") and the values to test |
| `text.py` | small helpers that pull phrases from stories ("I want to reset my password" → "reset the password") |
| `generate.py` | command-line script |
| `categories.json` | hand-typed categories for the example stories |
| `tests/` | pytest tests: 4 stories, all 6 categories, the numbers parser and the script |

## Tests

```bash
python -m pytest generator -q
```
