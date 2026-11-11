"""Pick the category of each acceptance criterion with the trained AI model.

The model is the requirement classifier (model/): a scikit-learn pipeline
saved to ``model/model.pkl`` by ``python model/train_new_model.py``.

    from generator import generate_with_model
    test_cases = generate_with_model(stories)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

from .core import CATEGORIES, _criteria, generate_for_stories
from .limits import extract_limits

MODEL_PATH = Path(__file__).resolve().parent.parent / "model" / "model.pkl"
LOW_CONFIDENCE = 0.5   # predictions below this are worth checking by hand

Prediction = Tuple[str, float]

# Jira formatting that says nothing about the category: "AC1:", "1.", "- ", "* ", "[ ]".
_LABEL_RE = re.compile(r"^\s*(?:(?:AC|A\.C\.)\s*\d+\s*[:.)-]\s*|\d+\s*[.)]\s+|[-*•–]\s+|\[[ xX]?\]\s*)+")

# A criterion with a numeric limit (length, count, attempts, money, %, size, time window) is a
# boundary criterion, unless it is about speed. The training data has almost no limits on time,
# money or percentages, so the model alone reads "The reset link expires after 30 minutes" as
# functional. Checked on project-grouped cross-validation and on data/jira_benchmark.csv.
_SPEED_RE = re.compile(
    r"\b(?:load\w*|respon\w*|fast|slow\w*|latency|throughput|concurrent|simultaneous|per\s+(?:second|minute|hour)"
    r"|peak|traffic|delay|freez\w*|smooth\w*|performance|quick\w*|speed|starts?\s+in|takes?|finish\w*"
    r"|process\w*|delivered|appear\w*|refresh\w*|ms|milliseconds?|fetch\w*|retriev\w*|quer\w*|search\w*|sync\w*)\b",
    re.IGNORECASE,
)


def clean_criterion(criterion: str) -> str:
    """Remove list markers and labels Jira adds ("AC2: ", "1. ", "- ") and collapse whitespace."""
    return re.sub(r"\s+", " ", _LABEL_RE.sub("", str(criterion))).strip()


def _has_limit(criterion: str) -> bool:
    return any(limit.kind != "other" or limit.currency or limit.unit == "%" for limit in extract_limits(criterion))


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
                             "'python model/train_new_model.py', or pass --categories with hand-typed categories")
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
        """One ``(category, confidence)`` pair per criterion, in the same order.

        The confidence is always the model's own probability for the returned category, so a
        criterion moved to ``boundary`` by the limit rule usually shows "please check".
        """
        if isinstance(criteria, str):  # a bare string would be classified letter by letter
            raise TypeError("predict() takes a list of criteria; wrap one criterion as [criterion]")
        if not criteria:
            return []
        texts = [clean_criterion(criterion) for criterion in criteria]
        predictions = []
        for text, row in zip(texts, self._pipeline.predict_proba(texts)):
            best = max(range(len(self._classes)), key=lambda index: row[index])
            category = self._classes[best]
            if category == "functional" and "boundary" in self._classes and _has_limit(text) \
                    and not _SPEED_RE.search(text):
                category = "boundary"
            predictions.append((category, round(float(row[self._classes.index(category)]), 2)))
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
