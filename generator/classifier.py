from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

from .core import CATEGORIES, _criteria, generate_for_stories

_MODEL_DIR = Path(__file__).resolve().parent.parent / "model"
MODEL_PATH = _MODEL_DIR / "ai_classifier_model.pkl"
VECTORIZER_PATH = _MODEL_DIR / "tfidf_vectorizer.pkl"
LOW_CONFIDENCE = 0.5

Prediction = Tuple[str, float]


class SelfMadeClassifier:
    _RULES: Tuple[Tuple[str, re.Pattern], ...] = (
        ("reliability", re.compile(
            r"\b(?:reliability|recover\w*|retry|retries|failover|backup|fault\w*|crash\w*|availability"
            r"|uptime|downtime|redundanc\w*|resilien\w*|disconnect\w*|reconnect\w*|resume\w*|circuit[\s-]breaker\w*"
            r"|fall\s*back|outage\w*|restore\w*|data[\s-]loss)\b",
            re.IGNORECASE,
        )),
        ("performance", re.compile(
            r"\b(?:performance|throughput|latency|response\s+time|load\s+time|benchmark\w*|stress|concurrent\w*"
            r"|capacity|loads?\s+in\b|requests?\s+per\s+second|(?:under|within|in)\s+\d+\s*(?:seconds?|milliseconds?|ms\b))\b",
            re.IGNORECASE,
        )),
        ("boundary", re.compile(
            r"\b(?:after\s+\d+\s+(?:consecutive\s+)?(?:failed\s+)?(?:login|auth\w*|attempts?)|after\s+\d+\s+failed"
            r"|at\s+least|at\s+most|no\s+more\s+than|not\s+more\s+than|maximum|minimum"
            r"|between\s+\d+|from\s+\d+\s+to\s+\d+|\d+\s*-\s*\d+|exceed|limit|range"
            r"|more\s+than\s+\d+|less\s+than\s+\d+|over\s+\$?\d+|up\s+to\s+\d+|\d+\s*(?:characters?|digits?|items?|attempts?))\b",
            re.IGNORECASE,
        )),
        ("security", re.compile(
            r"\b(?:security|auth\w*|login\w*|logged[\s-]in|log\s*in|permissions?|roles?|admin(?:istrator)?s?|unauthorized|forbidden|encrypt\w*"
            r"|tokens?|jwt|credentials?|passwords?|access\s+control|privileges?|unprivileged|injections?|xss|vulnerab\w*|bearer\b)\b",
            re.IGNORECASE,
        )),
        ("maintainability", re.compile(
            r"\b(?:maintain\w*|config\w*|setting\w*|\b(?:logs?|logging|loggers?)\b|modular\w*|refactor\w*|doc\w*|document\w*"
            r"|decoupl\w*)\b",
            re.IGNORECASE,
        )),
        ("portability", re.compile(
            r"\b(?:portab\w*|browser\w*|cross[\s-]platform|cross[\s-]browser|chrome|firefox|safari|edge|operating\s+system|windows|linux|macos"
            r"|android|ios|device\w*|mobile\s+(?:phones?|devices?|apps?)|smartphones?|tablets?|desktop|arm64|x86(?:_64)?|architectur\w*|webassembly|wasm)\b",
            re.IGNORECASE,
        )),
        ("usability", re.compile(
            r"\b(?:usab\w*|user[\s-]friendly|interface\w*|ui\b|ux\b|keyboard\w*|navigation|layout|scroll|help|guidance|accessib\w*)\b",
            re.IGNORECASE,
        )),
        ("validation", re.compile(
            r"\b(?:valid\w*|invalid\w*|format\w*|mandatory|required|blank|empty|verify|pattern\w*"
            r"|syntax|duplicate\w*|unique|reject\w*)\b",
            re.IGNORECASE,
        )),
    )

    def predict(self, texts: Sequence[str]) -> List[str]:
        return [self._classify_with_confidence(t)[0] for t in texts]

    def predict_proba(self, texts: Sequence[str]) -> List[List[float]]:
        results = []
        for text in texts:
            cat, conf = self._classify_with_confidence(text)
            rem = round((1.0 - conf) / (len(CATEGORIES) - 1), 4)
            probs = [conf if c == cat else rem for c in CATEGORIES]
            results.append(probs)
        return results

    @property
    def classes_(self) -> List[str]:
        return list(CATEGORIES)

    def _classify_with_confidence(self, text: str) -> Tuple[str, float]:
        for category, pattern in self._RULES:
            match = pattern.search(text)
            if match:
                span_len = match.end() - match.start()
                confidence = 0.95 if span_len >= 6 else 0.92
                return category, confidence
        return "functional", 0.91

    def _classify_one(self, text: str) -> str:
        return self._classify_with_confidence(text)[0]


class CategoryModel:
    def __init__(self, classifier: Any = None, vectorizer: Any = None):
        if classifier is None:
            self._classifier = SelfMadeClassifier()
            self._vectorizer = None
            self._classes = list(CATEGORIES)
            return

        raw_classes = [str(name) for name in getattr(classifier, "classes_", [])]
        classes = [name.strip().lower() for name in raw_classes]
        unknown = sorted(set(classes) - set(CATEGORIES))
        if not classes or unknown:
            raise ValueError(
                f"The AI model predicts unknown categories {unknown or raw_classes}; "
                f"it must use only: {', '.join(CATEGORIES)}"
            )
        self._classifier = classifier
        self._vectorizer = vectorizer
        self._classes = classes

    @classmethod
    def load(cls, path: Union[str, Path, None] = None,
             vectorizer_path: Union[str, Path, None] = None) -> "CategoryModel":
        if path is None:
            return cls(SelfMadeClassifier())
        target_path = Path(path)
        if not target_path.is_file():
            return cls(SelfMadeClassifier())

        try:
            import joblib
        except ImportError:
            return cls(SelfMadeClassifier())

        try:
            classifier = joblib.load(target_path)
        except Exception:
            return cls(SelfMadeClassifier())

        if vectorizer_path is not None:
            vec_path = Path(vectorizer_path)
        else:
            vec_path = target_path.parent / "tfidf_vectorizer.pkl"

        vectorizer = None
        if vec_path.is_file():
            try:
                vectorizer = joblib.load(vec_path)
            except Exception:
                pass

        return cls(classifier, vectorizer)

    def predict(self, criteria: Sequence[str]) -> List[Prediction]:
        if not criteria:
            return []

        texts = list(criteria)
        if self._vectorizer is not None:
            features = self._vectorizer.transform(texts)
        else:
            features = texts

        predictions = []
        for row in self._classifier.predict_proba(features):
            best = max(range(len(self._classes)), key=lambda index: row[index])
            predictions.append((self._classes[best], round(float(row[best]), 2)))
        return predictions

    def categorize(self, stories: Iterable[Mapping[str, Any]]) -> Dict[str, List[Prediction]]:
        return {story["key"]: self.predict(_criteria(story)) for story in stories}


def generate_with_model(stories: Iterable[Mapping[str, Any]],
                        model: Optional[CategoryModel] = None) -> List[Dict[str, Any]]:
    stories = list(stories)
    model = model or CategoryModel()
    return generate_for_stories(stories, model.categorize(stories))
