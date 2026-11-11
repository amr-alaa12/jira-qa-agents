"""Reproduce the classifier's evaluation numbers (README, "Results").

    python model/evaluate_classifier.py

1. Project-grouped 5-fold cross-validation on the REAL requirements: no DOSSPRE project is in
   both train and test; template-generated rows are only used for training.
2. data/jira_benchmark.csv: 120 Jira-style acceptance criteria (20 per category), never trained on.
Both use generator.CategoryModel, i.e. exactly what the app does (text clean-up + limit rule).
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import GroupKFold

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "model"))
from train_new_model import BENCHMARK_PATH, build_pipeline, load_dataset  # noqa: E402

from generator import CategoryModel  # noqa: E402
from generator.classifier import LOW_CONFIDENCE  # noqa: E402

warnings.filterwarnings("ignore", category=UserWarning)


def calibration_error(confidences, correct, bins=10):
    confidences, correct = np.asarray(confidences), np.asarray(correct)
    error = 0.0
    for low in np.linspace(0, 1, bins, endpoint=False):
        in_bin = (confidences > low) & (confidences <= low + 1 / bins)
        if in_bin.any():
            error += in_bin.mean() * abs(correct[in_bin].mean() - confidences[in_bin].mean())
    return error


def grouped_cross_validation(df, folds=5):
    real = df[df["source"] != "generated"]
    groups = real["project_id"].astype(str).where(real["source"] == "dosspre", "hw" + real.index.astype(str))
    truth, predicted, confidence = [], [], []
    for train_idx, test_idx in GroupKFold(folds).split(real, real["category"], groups):
        train = pd.concat([df[df["source"] == "generated"], real.iloc[train_idx]])
        model = CategoryModel(build_pipeline().fit(train["text"], train["category"]))
        test = real.iloc[test_idx]
        for (category, conf), actual in zip(model.predict(list(test["text"])), test["category"]):
            truth.append(actual)
            predicted.append(category)
            confidence.append(conf)
    return truth, predicted, confidence


def summarise(name, truth, predicted, confidence):
    correct = np.array(truth) == np.array(predicted)
    confident = np.array(confidence) >= LOW_CONFIDENCE
    print(f"\n== {name}: accuracy {accuracy_score(truth, predicted):.1%}, "
          f"macro-F1 {f1_score(truth, predicted, average='macro'):.3f}, "
          f"calibration error {calibration_error(confidence, correct):.3f}")
    print(f"   flagged 'please check' (< {LOW_CONFIDENCE}): {1 - confident.mean():.0%}; "
          f"accuracy of the rest {correct[confident].mean():.1%}")
    print(classification_report(truth, predicted, zero_division=0))


def main():
    df = load_dataset()
    summarise("Project-grouped 5-fold CV on real requirements", *grouped_cross_validation(df))
    bench = pd.read_csv(BENCHMARK_PATH, encoding="utf-8")
    model = CategoryModel.load()
    predictions = model.predict(list(bench["text"]))
    summarise("Jira-style benchmark, model/model.pkl", list(bench["category"]),
              [p[0] for p in predictions], [p[1] for p in predictions])


if __name__ == "__main__":
    main()
