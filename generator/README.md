# Test Case Generator (Member 4)

Takes a user story, lets the AI model (the requirement classifier, `model/model.pkl`) pick the category of each acceptance criterion, and writes test cases in the agreed format (`examples/test_cases.json`). Since the 21/10 meeting every test case also has an `input` field, so each result states its **input** and its **expected output**.

**Input → output:** `stories.json` → AI model categories → `test_cases.json`

```json
{
  "story_key": "SHOP-1",
  "id": "SHOP-1-TC3",
  "title": "New password with 7 characters is rejected",
  "type": "boundary",
  "input": "New password: 7 characters",
  "steps": ["Open the reset password page", "Enter a new password with 7 characters", "Submit the form"],
  "expected": "The new password is rejected and an error message explains the limit (at least 8 characters)"
}
```

## Run it

From the repository root:

```bash
pip install -r generator/requirements.txt
python model/train_and_predict.py           # once: trains and saves model/model.pkl
python generator/generate.py                # examples/stories.json -> generator/test_cases.json
```

The script prints the category the model chose for every criterion with its confidence, and marks predictions below 0.5 with `<- low confidence, please check`:

```text
SHOP-1: The user receives a reset link by email -> functional (0.69)
SHOP-1: The new password must be at least 8 characters -> boundary (0.87)
Wrote 5 test cases for 1 story to generator/test_cases.json
```

Options:

```bash
python generator/generate.py path/to/stories.json \
    --model model/model.pkl \
    --output generator/test_cases.json
```

To skip the model (for example to fix a wrong prediction), pass `--categories` with a JSON file of hand-typed categories: one list per story key, one category per acceptance criterion, in the same order. `generator/categories.json` is an example:

```json
{ "SHOP-1": ["functional", "boundary"] }
```

On bad input the script prints a clear `Error: ...` message and exits with code 1. Bad input means: a missing file, invalid JSON, a missing or unloadable model, a story with no categories, an unknown category, or a different number of categories than criteria.

## Use it from code (for `main.py`)

```python
from generator import generate_with_model

test_cases = generate_with_model(stories)   # loads model/model.pkl and classifies every criterion
```

To reuse one loaded model, or to see the predictions:

```python
from generator import CategoryModel, generate_test_cases

model = CategoryModel.load()                               # or CategoryModel.load("path/to/model.pkl")
categories = model.predict(story["acceptance_criteria"])   # [("functional", 0.69), ("boundary", 0.87)]
test_cases = generate_test_cases(story, categories)
```

`generate_test_cases(story, ["functional", "boundary"])` also accepts plain category names. `generate_for_stories(stories, {"SHOP-1": [...], ...})` does the same for a list of stories. Ids are `<story key>-TC1`, `-TC2`, … and are numbered separately for each story.

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
| `classifier.py` | `CategoryModel` (loads the AI model) and `generate_with_model()` |
| `core.py` | `generate_test_cases()` and `generate_for_stories()`, input checks |
| `templates.py` | one template per category |
| `limits.py` | finds numeric limits ("at least 8 characters") and the values to test |
| `text.py` | small helpers that pull phrases from stories ("I want to reset my password" → "reset the password") |
| `generate.py` | command-line script |
| `categories.json` | hand-typed categories for the example stories (used with `--categories`) |
| `tests/` | pytest tests: 4 stories, all 6 categories, the AI model integration, the numbers parser and the script |

## Tests

```bash
python -m pytest generator -q
```
