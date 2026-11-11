"""Run the classifier on real Jira acceptance criteria and save a review sheet.

1. python jira/fetch.py KAN                      -> stories.json
2. python model/evaluate_jira_criteria.py       -> model/jira_criteria_results.csv
3. Open the CSV, fill the 'manual_category' column, then run with --summary.
"""
import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from generator import CategoryModel  # noqa: E402

RESULTS = ROOT / "model" / "jira_criteria_results.csv"
FIELDS = ["story_key", "criterion", "predicted_category", "confidence", "manual_category"]


def write_sheet(stories_path, limit):
    stories = json.loads(Path(stories_path).read_text(encoding="utf-8"))
    rows = [(s["key"], c) for s in stories for c in s.get("acceptance_criteria", [])][:limit]
    predictions = CategoryModel.load().predict([criterion for _, criterion in rows])
    with RESULTS.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        for (key, criterion), (category, confidence) in zip(rows, predictions):
            writer.writerow({"story_key": key, "criterion": criterion, "predicted_category": category,
                             "confidence": confidence, "manual_category": ""})
    print(f"Wrote {len(rows)} criteria to {RESULTS}. Fill 'manual_category', then run --summary.")


def summary():
    rows = list(csv.DictReader(RESULTS.open(encoding="utf-8")))
    checked = [r for r in rows if r["manual_category"].strip()]
    correct = [r for r in checked if r["manual_category"].strip().lower() == r["predicted_category"]]
    print(f"Checked {len(checked)} / {len(rows)}; correct {len(correct)} "
          f"({len(correct) / max(len(checked), 1):.0%})")
    confusions = Counter((r["manual_category"].strip().lower(), r["predicted_category"])
                         for r in checked if r not in correct)
    for (truth, predicted), n in confusions.most_common():
        print(f"  {truth} predicted as {predicted}: {n}")
    low = [r for r in checked if float(r["confidence"]) < 0.5]
    print(f"Low confidence (< 0.5): {len(low)}, of which wrong: {sum(r not in correct for r in low)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stories", nargs="?", default=str(ROOT / "stories.json"))
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    summary() if args.summary else write_sheet(args.stories, args.limit)
