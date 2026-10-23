"""Pick the category of each acceptance criterion with the trained AI model.

The model is the requirement classifier (Member 3): a scikit-learn pipeline
saved to ``model/model.pkl`` by ``python model/train_and_predict.py``.

    from generator import generate_with_model
    test_cases = generate_with_model(stories)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

from .core import CATEGORIES, _criteria, generate_for_stories

MODEL_PATH = Path(__file__).resolve().parent.parent / "model" / "model.pkl"
LOW_CONFIDENCE = 0.5   # predictions below this are worth checking by hand

Prediction = Tuple[str, float]


class CategoryModel:
    """The trained classifier: criterion text -> (category, confidence)."""

    def __init__(self, pipeline: Any):
        classes = [str(name) for name in getattr(pipeline, "classes_", [])]
        unknown = sorted(set(classes) - set(CATEGORIES))
        if not classes or unknown:
            raise ValueError(f"The AI model predicts unknown categories {unknown or classes}; "
                             f"it must use only: {', '.join(CATEGORIES)}")
        self._pipeline = pipeline
        self._classes = classes

    @classmethod
    def load(cls, path: Union[str, Path, None] = None) -> "CategoryModel":
        """Load ``model/model.pkl`` (or ``path``)."""
        path = Path(path) if path else MODEL_PATH
        if not path.is_file():
            raise ValueError(f"The AI model was not found: {path}. Train it with "
                             "'python model/train_and_predict.py', or pass --categories with hand-typed categories")
        try:
            import joblib
        except ImportError:
            raise ValueError("The AI model needs scikit-learn and joblib: pip install -r requirements.txt") from None
        try:
            pipeline = joblib.load(path)
        except Exception as error:  # a broken or incompatible pickle can raise almost anything
            raise ValueError(f"Cannot load the AI model {path}: {error}") from None
        return cls(pipeline)

    def predict(self, criteria: Sequence[str]) -> List[Prediction]:
        """One ``(category, confidence)`` pair per criterion, in the same order."""
        if not criteria:
            return []
        predictions = []
        for row in self._pipeline.predict_proba(list(criteria)):
            best = max(range(len(self._classes)), key=lambda index: row[index])
            predictions.append((self._classes[best], round(float(row[best]), 2)))
        return predictions

    def categorize(self, stories: Iterable[Mapping[str, Any]]) -> Dict[str, List[Prediction]]:
        """Map each story key to the predictions for its criteria (the input of ``generate_for_stories``)."""
        return {story["key"]: self.predict(_criteria(story)) for story in stories}


def generate_with_model(stories: Iterable[Mapping[str, Any]],
                        model: Optional[CategoryModel] = None) -> List[Dict[str, Any]]:
    """Classify every criterion with the AI model, then generate the test cases."""
    stories = list(stories)
    model = model or CategoryModel.load()
    return generate_for_stories(stories, model.categorize(stories))
