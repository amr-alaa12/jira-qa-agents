"""Predict the category of one requirement with the trained model (model/model.pkl).

Train the model with:  python model/train_new_model.py
Uses generator.CategoryModel, so this gives exactly what the app and the generator give
(same text clean-up and the same rule for numeric limits).
"""
import sys
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from generator import CategoryModel  # noqa: E402


@lru_cache(maxsize=1)
def _load_model():
    """Load model/model.pkl once, whatever the current working directory is."""
    return CategoryModel.load()


def predict_category(sentence):
    """Return (category, confidence) for one sentence."""
    return _load_model().predict([sentence])[0]


if __name__ == "__main__":
    print(predict_category("The page loads in under 2 seconds"))
