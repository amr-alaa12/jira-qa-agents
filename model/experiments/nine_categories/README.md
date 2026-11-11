# Nine-category experiment (archived)

Ahmed's first experiment: a classifier with nine UPPERCASE categories
(the six team categories plus RELIABILITY, PORTABILITY and MAINTAINABILITY).

It is **kept for reference and is not used by the app or the generator**:
the generator only has templates for the six team categories, so the app uses
`model/model.pkl` (trained by `model/train_new_model.py`).

The files are unchanged except for the data path in `train_nine_categories.py`,
which now points three folders up because the script moved here.

    python model/experiments/nine_categories/train_nine_categories.py
    python model/experiments/nine_categories/evaluateNewModel.py
