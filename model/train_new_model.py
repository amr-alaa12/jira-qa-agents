"""Train the requirement classifier and save it as ONE pipeline: model/model.pkl.

Run from anywhere:  python model/train_new_model.py
The saved pipeline takes raw text, so the app and the generator can use it
directly (generator.CategoryModel.load()).

Evaluation is honest about where the model will be used:
- DOSSPRE requirements are split BY PROJECT, so no project is in both train and test;
- template-generated rows are only ever used for training;
- data/jira_benchmark.csv (120 Jira-style acceptance criteria, 20 per category) is never trained on.
After evaluation the final model is trained on ALL rows, so no labelled data is thrown away.
"""
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import FeatureUnion, Pipeline

MODEL_DIR = Path(__file__).resolve().parent
DATA_DIR = MODEL_DIR.parent / "data"
CSV_PATH = DATA_DIR / "requirements_merged_with_dosspre_new.csv"
BENCHMARK_PATH = DATA_DIR / "jira_benchmark.csv"
MODEL_PATH = MODEL_DIR / "model.pkl"

# The six categories the generator has templates for (see generator/core.py).
CATEGORIES = ["functional", "validation", "boundary", "security", "performance", "usability"]

# Keep one-character tokens, digits and the symbols that signal limits and formats ($, %, @).
TOKEN_PATTERN = r"(?u)\b\w+\b|[$€£%@]"


def load_dataset(path=CSV_PATH):
    df = pd.read_csv(path, encoding="utf-8")
    df = df.dropna(subset=["text", "category"])
    df["category"] = df["category"].str.strip().str.lower()
    dropped = df[~df["category"].isin(CATEGORIES)]
    print(f"Dropped {len(dropped)} rows outside the six categories: "
          f"{dropped['category'].value_counts().to_dict()}")
    return df[df["category"].isin(CATEGORIES)].copy()


def build_pipeline():
    """Word 1-2-grams WITHOUT stop-word removal, plus character n-grams.

    English stop-word lists drop exactly the words that decide the category here:
    "only", "not", "cannot", "must", "at least", "more", "less", "within", "under", "empty".
    Character n-grams make the model robust to word forms ("validate", "validation", "invalid").
    """
    words = TfidfVectorizer(ngram_range=(1, 2), token_pattern=TOKEN_PATTERN, sublinear_tf=True)
    chars = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True, min_df=2)
    return Pipeline([
        ("features", FeatureUnion([("words", words), ("chars", chars)])),
        ("clf", LogisticRegression(C=10.0, max_iter=3000, class_weight="balanced")),
    ])


def split_by_project(df, test_size=0.3, seed=42):
    """Real rows only; DOSSPRE grouped by project, each hand-written row is its own group."""
    real = df[df["source"] != "generated"]
    groups = real["project_id"].astype(str).where(real["source"] == "dosspre", "hw" + real.index.astype(str))
    train_idx, test_idx = next(GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
                               .split(real, real["category"], groups))
    return real.iloc[train_idx], real.iloc[test_idx]


def main():
    df = load_dataset()
    print(df["category"].value_counts(), "\n")

    real_train, real_test = split_by_project(df)
    train = pd.concat([df[df["source"] == "generated"], real_train])
    pipeline = build_pipeline().fit(train["text"], train["category"])
    print(f"Evaluation on {len(real_test)} held-out REAL requirements (unseen projects):")
    print(classification_report(real_test["category"], pipeline.predict(real_test["text"]), zero_division=0))

    final = build_pipeline().fit(df["text"], df["category"])
    if BENCHMARK_PATH.is_file():
        bench = pd.read_csv(BENCHMARK_PATH, encoding="utf-8")
        print(f"Jira-style benchmark ({len(bench)} criteria, never trained on), final model:")
        print(classification_report(bench["category"], final.predict(bench["text"]), zero_division=0))

    joblib.dump(final, MODEL_PATH, compress=3)
    print(f"Saved {MODEL_PATH} (trained on all {len(df)} rows)")


if __name__ == "__main__":
    main()
