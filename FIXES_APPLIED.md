# Fixes applied after the code review (10 Nov 2026)

Every task in the five correction PDFs is applied here. The core idea and the core
code were kept: the same modules, the same templates, the same Jira API calls and
the same Streamlit layout. Only defects were fixed, and nothing was deleted.
Ahmed's nine-category experiment is kept in `model/experiments/`, and the HTML
mock-up is kept in `docs/prototype/`.

Checked: 101 tests pass (94 before plus 7 new regression tests), the linter
reports no problems, and the app works when started from any folder.

## Amr — shared files and Jira connector
- R1 `jira/fetch.py`: `adf_to_text` keeps each criterion whole (bold text, links, line breaks, @mentions).
- R2 `jira/fetch.py`: no Streamlit import; new `setting()` reads Streamlit secrets or `.env`.
- R3 `jira/fetch.py`: `fetch_stories` only returns stories; `save_stories` writes `stories.json` from the command line.
- R4 `README.md`: quick start, commands, structure, test-case format; the original text is kept under "Vision".
- R5 `requirements.txt`: one file with pinned versions; `generator/requirements.txt` removed; devcontainer installs Streamlit once.
- R6 `.gitignore`: `model/model.pkl` is no longer ignored; `generator/test_cases.json` is.
- R7 `app/FrontEnd/` moved, unchanged, to `docs/prototype/`.
- R8 `tests/test_fetch.py` and `pytest.ini`: `python -m pytest -q` runs all tests.
- R9 `jira/list_fields.py`: runs only from the command line and uses `setting()`.

## Omar — data
- O1 `data/validate_dataset.py`: checks any CSV (`requirements.csv` by default); `--extra-labels` for the merged file.
- O2 `data/PAIRED_DATASET.md`: report template. **The dataset search is still Omar's task.**
- O3, O4 `data/README.md`: files table, real counts, what the merged file contains, new validator commands, sources section.
- O5 `data/build_dataset.py`: one import per line, writes only when run (output checked to be byte-identical).

## Ahmed — classifier
- A1 `model/train_new_model.py`: six lowercase categories, one Pipeline saved as `model/model.pkl` (retrained).
- A2 Evaluation on held-out real requirements: 74% (previously 36.6%); results in `model/README.md`.
- A3 `predict_category`: works from any folder, loads the model once.
- A4 `model/train_and_predict.py`: no GitHub download; only `predict_category`.
- A5 CSV read as UTF-8.
- A6 `model/evaluate_jira_criteria.py` replaces `evaluateNewModel.py` (the original is kept in `model/experiments/`).
  **Filling the sheet with real KAN criteria needs Jira access and a manual check by Ahmed.**
- A7 `model/README.md`.

## Zayd — generator
- Z1 Field `expected` renamed to `expected_output` (code, tests, examples, README).
- Z2 `generate.py`: no crash for stories without acceptance criteria.
- Z3 `templates.py`: `card` and `phone` match whole words only.
- Z4 `templates.py`: titles written as "As a user I want to ..." are not used as page names.
- Z5 `text.py` `outcome()`: Given / When / Then criteria give short titles.
- Z6 `templates.py`: "accepted" is recognised in boundary rules.
- Z7 `examples/test_cases.json` updated to the final format.
- Z8 "Member 3 / Member 4" replaced by component names.
- New tests: `generator/tests/test_review_fixes.py` and one new test in `test_cli.py`.

## Moataz — Streamlit app
- M1 shows `expected_output`.
- M2 loads the model once with `generator.CategoryModel` (`st.cache_resource`), and predicts once per story.
- M3 uses `JIRA_PROJECT_KEY`; calls Jira at most every 5 minutes, and remembers failures too.
- M4 `width="stretch"` instead of the deprecated `use_container_width`.
- M5 "About" text describes the real loading order.
- M6 CSS indentation.
- M7 message for stories without acceptance criteria.

## Still to do by people (cannot be done in code)
- Omar: find the paired story / test-case dataset; fill in the DOSSPRE source and licence.
- Ahmed: run `model/evaluate_jira_criteria.py` on real KAN criteria and check them by hand.
- Amr: final run with the real Jira project; comparison table and paper summaries in `docs/`.
- Moataz: screenshot of a test case with Input and Expected output.

## Negative test cases: logical expected output (11 Nov 2026)
- Bug: functional negative cases ended with "and this does not happen: <outcome>", pasting the
  requirement itself ("…and this does not happen: the review should be saved successfully").
- `generator/text.py`: new `affirm()` (requirement → observation: "the review is saved successfully"),
  `negate()` (its logical opposite: "the review is not saved"; coordinated verbs become "does not A or B"),
  `is_failure_outcome()` and `precondition()` (the "Given" part, rewritten about the user).
- `generator/templates.py` (`functional`): positive cases use `affirm()`; negative cases assert `negate()`.
  Outcomes that are themselves an error path ("the payment is rejected") are not negated into a success and
  get no "confirmation message". If an outcome cannot be negated safely it is quoted as the result that must
  not occur. A "Given" clause becomes a setup step in every case.
- `generator/tests/test_negative_outcomes.py`: 18 regression tests. `examples/test_cases.json` updated.
- Follow-up: outcomes that are already negative ("no automatic reply is sent") are never negated again
  (no "no … is not sent"), and "I/me/my" in an outcome is rewritten as "the user".

## Generator audit (11 Nov 2026)
About 3,200 generated test cases (every criterion in `data/requirements.csv` plus 25 Jira-style
Given/When/Then criteria, through every template) were checked for logical and wording defects. Fixed:
- `limits.py`: a negation before a limit turns it around — "cannot be longer than 12 characters" now
  accepts 12 and rejects 13 (13 used to be accepted).
- `text.py`: subjects are split at an auxiliary first ("The display name cannot…" → "display name", not
  "the"); Given/When/Then, leading "After…," clauses and "I/me/my" are handled everywhere; capitalised UI
  labels ("clicks Save") are never read as verbs; "only X can…" and permissions are never negated.
- `templates.py`:
  - boundary: limits on what a person may do read "Cancel an order after 25 hours: refused"
    (not "The customer is rejected"); no "Comment with with…"; correct articles.
  - functional: titles state observations; permissions are not "revoked" by a failed form.
  - validation: the field is never an actor ("Valid system is accepted" → "Valid payment information…").
  - security: named groups are compared ("Deactivated user cannot log in" vs "User who is not
    deactivated"), other users' data, data-protection criteria check storage and traffic, "Only a manager"
    and guests are handled.
  - page names come from the noun of a verb title ("Manage user accounts" → "the user accounts page");
    "email notification" is not an email field; performance titles agree with plural subjects.
- `generator/tests/test_negative_outcomes.py`: 16 more regression tests (165 pass).

## Classifier audit (11 Nov 2026)
- **Bug — stop words:** `TfidfVectorizer(stop_words="english")` removed *only, not, cannot, must, at
  least, more, less, within, under, empty* — the words that separate security, boundary and validation.
  "Only admins can delete products" reached the model as "admins delete products" (predicted functional).
- **Bug — numbers:** the default token pattern dropped one-digit numbers and `$ %`.
- **Gap — evaluation leaked:** the test split was not grouped by DOSSPRE project; now project-grouped.
- **Gap — final model threw away 30% of the real data:** it is now trained on all rows after evaluation.
- **Gap — no Jira-style test:** `data/jira_benchmark.csv` (120 criteria) added, evaluation only.
- **Gap — inconsistent entry points:** `model/train_and_predict.py` now uses `generator.CategoryModel`.
- New: character n-grams, Jira list-marker clean-up, numeric-limit rule for boundary (see `model/README.md`).
- Results: grouped CV 70.4% → 76.1% (macro-F1 0.726 → 0.816), calibration error 0.134 → 0.060,
  Jira benchmark 80.8% → 85.8%, "please check" flags 39% → 14%. 12 new tests (177 pass).

## Live-site review after merging PRs #2 and #3 (11 Nov 2026)
- **"Incorrect passwords must be rejected"** produced password-*format* cases (too weak, spaces only).
  It now tests a wrong password for a registered account, and the wrong letter case, whatever the category.
- **"Only authenticated users can …"** treated "authenticated users" as a user group. Authenticated,
  logged-in, signed-in and registered are now a login state: logged-in user vs anonymous visitor.
- **"An empty search must show a helpful message"** produced "Valid empty search is accepted". It now
  tests an empty input, spaces only, and real text (message not shown).
- **"Search results must match the entered product name"** produced name-format cases. It now tests
  an existing name and a name that matches nothing.
- `CategoryModel.predict("one string")` classified the string letter by letter; it now raises `TypeError`.
- Not changed: the model still labels "Search results must match …" as *validation* (74%). Every
  "search results" row in the training data is a performance requirement. Adding 25 hand-written
  functional rows lowered the Jira benchmark from 85.8% to 82%, so it was reverted; the test cases
  are correct either way.
