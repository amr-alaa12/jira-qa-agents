# Test Case Generator (Member 4)

Takes a user story, categorizes each acceptance criterion across 9 requirement categories, and produces structured test cases. Each test case states its concrete input, steps, and expected output.

**Input -> output:** `stories.json` -> 9 categories -> `test_cases.json` / CSV / Excel / Gherkin / Xray / Playwright / Cypress

## Standard Test Case Format

The primary core attributes are always generated:

```json
{
  "story_key": "SHOP-1",
  "id": "SHOP-1-TC4",
  "title": "New password with 7 characters is rejected",
  "type": "boundary",
  "input": "New password: \"Passw0r\" (7 characters)",
  "steps": [
    "Open the reset password page",
    "Enter \"Passw0r\" (7 characters) in the new password field",
    "Submit the form"
  ],
  "expected": "The new password is rejected, the form is not submitted and an error message explains the limit (at least 8 characters)"
}
```

Optional enterprise attributes (`priority`, `preconditions`, `execution_type`, `gherkin`) are generated when requested (`--optional` or `include_optional=True`):

```json
{
  "priority": "High",
  "preconditions": [
    "User is on the open the reset password page with active connectivity"
  ],
  "execution_type": "automated",
  "gherkin": "Scenario: New password with 7 characters is rejected\n  Given Open the reset password page\n  When Enter \"Passw0r\" (7 characters) in the new password field\n  And Submit the form\n  Then The new password is rejected, the form is not submitted and an error message explains the limit (at least 8 characters)"
}
```

## Run it

From the repository root:

```bash
python generator/generate.py
```

CLI Options:

```bash
python generator/generate.py examples/stories.json --output generator/test_cases.json
python generator/generate.py examples/stories.json --optional
python generator/generate.py examples/stories.json --deduplicate
python generator/generate.py examples/stories.json --format csv --output test_cases.csv
python generator/generate.py examples/stories.json --format excel --output test_cases.xlsx
python generator/generate.py examples/stories.json --format gherkin --output test_cases.feature
python generator/generate.py examples/stories.json --format xray --output xray_tests.json
python generator/generate.py examples/stories.json --format playwright --output test_spec.py
python generator/generate.py examples/stories.json --format cypress --output test_spec.cy.ts
```

## Use it from code

```python
from generator import generate_test_cases

test_cases = generate_test_cases(story, ["functional", "boundary"])
```

With optional attributes and deduplication:

```python
test_cases = generate_test_cases(
    story,
    ["functional", "boundary"],
    include_optional=True,
    deduplicate=True,
)
```

Exporting to various formats:

```python
from generator import to_csv, to_cypress_ts, to_excel, to_gherkin_feature, to_playwright_python, to_xray_json

csv_string = to_csv(test_cases)
to_excel(test_cases, "test_cases.xlsx")
gherkin_feature = to_gherkin_feature(story, test_cases)
xray_payload = to_xray_json(test_cases)
playwright_code = to_playwright_python(story, test_cases)
cypress_code = to_cypress_ts(story, test_cases)
```

To generate for multiple stories:

```python
from generator import generate_for_stories

test_cases = generate_for_stories(stories, {"SHOP-1": ["functional", "boundary"]})
```

Using the self-made category classifier:

```python
from generator import CategoryModel, generate_with_model

model = CategoryModel()
categories = model.predict(story["acceptance_criteria"])
test_cases = generate_with_model(stories, model=model)
```

## Supported Categories (9 Total)

1. **functional** - Core business logic and end-to-end user actions.
2. **validation** - Input data format checks, mandatory/optional fields, and error messages.
3. **boundary** - Edge cases at, just below, and just above numeric/length thresholds.
4. **security** - Role-based permissions, authentication status, and data protection.
5. **performance** - Single-user response times and concurrent load limits.
6. **usability** - Navigation, mobile responsiveness, keyboard accessibility, and clarity.
7. **reliability** - Network dropouts, service errors, and recovery.
8. **portability** - Cross-browser (Chrome, Firefox, Safari) and cross-OS behavior.
9. **maintainability** - Modularity, config isolation, and logging.

## Run tests

```bash
pytest generator -v
```
