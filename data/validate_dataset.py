"""Check a requirements CSV before it is used for training.

Usage (from anywhere):
    python data/validate_dataset.py                                   # data/requirements.csv
    python data/validate_dataset.py data/requirements_merged_with_dosspre_new.csv --extra-labels
"""
import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent
DEFAULT_CSV = DATA_DIR / "requirements.csv"

REQUIRED_COLUMNS = {"text", "category"}
OPTIONAL_COLUMNS = {"project_id", "source"}
SIX_LABELS = {"functional", "validation", "boundary", "security", "performance", "usability"}
EXTRA_LABELS = {"reliability", "portability", "maintainability"}
MIN_ROWS = 1000
MIN_EXAMPLES_PER_CATEGORY = 50


def validate(path, labels):
    errors = []
    with open(path, newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        columns = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - columns
        unknown = columns - REQUIRED_COLUMNS - OPTIONAL_COLUMNS
        if missing or unknown:
            return [f"bad columns: missing {sorted(missing)}, unknown {sorted(unknown)}"], Counter(), 0
        rows = list(reader)

    counts, seen = Counter(), set()
    for line, row in enumerate(rows, start=2):
        text = (row.get("text") or "").strip()
        category = (row.get("category") or "").strip().lower()
        if not text:
            errors.append(f"line {line}: empty text")
        if "source" in columns and not (row.get("source") or "").strip():
            errors.append(f"line {line}: empty source")
        if category not in labels:
            errors.append(f"line {line}: bad category '{category}'")
        else:
            counts[category] += 1
        key = text.casefold()
        if key and key in seen:
            errors.append(f"line {line}: duplicate text '{text}'")
        seen.add(key)

    if len(rows) < MIN_ROWS:
        errors.append(f"fewer than {MIN_ROWS} rows")
    for category in sorted(labels):
        if counts[category] < MIN_EXAMPLES_PER_CATEGORY:
            errors.append(f"{category} has fewer than {MIN_EXAMPLES_PER_CATEGORY} examples")
    return errors, counts, len(rows)


def main():
    parser = argparse.ArgumentParser(description="Validate a requirements dataset.")
    parser.add_argument("csv", nargs="?", default=str(DEFAULT_CSV))
    parser.add_argument("--extra-labels", action="store_true",
                        help="also accept reliability, portability and maintainability")
    args = parser.parse_args()
    labels = SIX_LABELS | EXTRA_LABELS if args.extra_labels else SIX_LABELS

    try:
        errors, counts, total = validate(args.csv, labels)
    except FileNotFoundError:
        sys.exit(f"ERROR: dataset not found: {args.csv}")

    print(f"{args.csv}\nRows: {total}")
    for category in sorted(labels):
        print(f"  {category:15s} {counts[category]}")
    if errors:
        print("\nPROBLEMS:")
        for error in errors[:30]:
            print(" -", error)
        if len(errors) > 30:
            print(f" ... and {len(errors) - 30} more problems")
        sys.exit(1)
    print("\nOK - dataset is valid.")


if __name__ == "__main__":
    main()
