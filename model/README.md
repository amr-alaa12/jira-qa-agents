# Requirement classifier

Predicts the category of one acceptance criterion: `functional`, `validation`,
`boundary`, `security`, `performance` or `usability` (the six team categories).
The app and the generator load it with `generator.CategoryModel.load()`.

## Files

| File | Purpose |
|---|---|
| `model.pkl` | **the only model the app uses**: one scikit-learn Pipeline (word + character TF-IDF, logistic regression), six lowercase categories |
| `train_new_model.py` | the only training script: `data/` → `model.pkl` |
| `train_and_predict.py` | `predict_category(sentence)` → `(category, confidence)` |
| `evaluate_classifier.py` | reproduces the results below (grouped CV + Jira benchmark) |
| `evaluate_jira_criteria.py` | runs the model on real Jira criteria and saves a sheet to check by hand |
| `experiments/nine_categories/` | archived nine-category experiment, not used by the app |

## Train

```bash
python model/train_new_model.py
```

Data: `data/requirements_merged_with_dosspre_new.csv`. Rows outside the six
categories (reliability, portability, maintainability: 192 rows) are dropped.
The test set is 30% of the **real** requirements (`source` ≠ `generated`) and is
never used for training. All template-generated rows are used for training only.

Trained with **scikit-learn 1.9.1**. A saved model only loads reliably with the
same version, so keep `requirements.txt` pinned to it.

## How it works

- **Features:** word 1–2-grams **without stop-word removal** (the English list drops *only, not,
  cannot, must, at least, more, less, within, under, empty* — the words that decide the category),
  digits and `$ % @` kept as tokens, plus character 2–5-grams for word forms
  (*validate / validation / invalid*). Logistic regression, `C=10`, balanced class weights.
- **Text clean-up:** Jira list markers and labels (`AC1:`, `1.`, `- `, `[ ]`) are removed before
  classifying (`generator.classifier.clean_criterion`).
- **Limit rule:** when the model says *functional* but the criterion has a numeric limit
  (`generator.limits.extract_limits`: length, count, attempts, money, %, size, a time window) and
  no speed wording, the category becomes *boundary*. The training data has almost no limits on time,
  money or percentages (one "%" and no "$" in 2,261 rows), so the model alone reads
  *"The reset link expires after 30 minutes"* as functional. The confidence shown is still the
  model's own probability, so these usually show "please check".
- The final model is trained on **all** rows after evaluation.

## Results

Reproduce with `python model/evaluate_classifier.py`. Both tests run through
`generator.CategoryModel`, exactly like the app.

| Test | Old model | **Current model** |
|---|---|---|
| Real requirements, project-grouped 5-fold CV (1,158 rows; no project in train and test) | 70.4% · macro-F1 0.726 | **76.1% · macro-F1 0.816** |
| Calibration error on that CV (lower = confidence means what it says) | 0.134 | **0.060** |
| Jira-style benchmark `data/jira_benchmark.csv` (120 criteria, 20 per category, never trained on) | 80.8% | **85.8%** |
| Benchmark, criteria with confidence ≥ 0.5 (not "please check") | — | **93.7%** (79% of criteria) |
| Criteria flagged "please check" in the CV | 39% | **14%** |

Per category on the grouped CV: boundary F1 0.90, validation 0.91, usability 0.85,
performance 0.77, security 0.75, functional 0.72.

Known limits:

- **Training data does not look like Jira:** 1,283 DOSSPRE rows are system specifications
  ("The system shall …"), not acceptance criteria; there are no Given/When/Then rows. The benchmark
  measures the gap, but more real, labelled Jira criteria are the real fix
  (`model/evaluate_jira_criteria.py` builds that sheet).
- **boundary and validation** have only 32 and 35 real rows (DOSSPRE has none); most of their
  training rows are template-generated.
- **Criteria about results or displayed output** ("Search results must match the entered name")
  can be read as validation: in the training data every "search results" row is performance and
  "must match" is almost always validation. The generator produces the right cases regardless.
- **functional vs security** remain the most confused pair (access-control wording such as
  *"Guests cannot post comments"* is rare in the data).
- The benchmark was written by the team that tuned the model; it is a sanity check, not an
  independent test set. Reliability, portability and maintainability (192 rows) are not predicted.

## Check on real Jira criteria

```bash
python jira/fetch.py KAN                      # saves stories.json
python model/evaluate_jira_criteria.py        # saves model/jira_criteria_results.csv
# fill the manual_category column by hand, then:
python model/evaluate_jira_criteria.py --summary
```
