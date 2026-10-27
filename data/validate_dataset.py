
import csv
import os
import sys
from collections import Counter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PATH = os.path.join(
    BASE_DIR,
    "requirements_merged_with_dosspre_new.csv"
)

EXPECTED_COLUMNS = [
    "project_id",
    "text",
    "category",
    "source",
]

LABELS = {
    "functional",
    "validation",
    "boundary",
    "security",
    "performance",
    "usability",
    "reliability",
    "portability",
    "maintainability",
}

MIN_ROWS = 1000
MIN_EXAMPLES_PER_CATEGORY = 50

errors = []

# Read and validate CSV structure
try:
    with open(PATH, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        if reader.fieldnames != EXPECTED_COLUMNS:
            print(
                "ERROR: Invalid CSV columns.\n"
                f"Expected: {EXPECTED_COLUMNS}\n"
                f"Got:      {reader.fieldnames}"
            )
            sys.exit(1)

        rows = list(reader)

except FileNotFoundError:
    print(f"ERROR: Dataset not found at {PATH}")
    sys.exit(1)

# Validate each row exactly once
counts = Counter()
seen = set()

for i, row in enumerate(rows, start=2):
    project_id = (row.get("project_id") or "").strip()
    text = (row.get("text") or "").strip()
    category = (row.get("category") or "").strip().lower()
    source = (row.get("source") or "").strip()

    # project_id may be missing for some dataset rows.
    # Missing project IDs are allowed.

    if not text:
        errors.append(f"line {i}: empty text")

    if not source:
        errors.append(f"line {i}: empty source")

    if category not in LABELS:
        errors.append(f"line {i}: bad category '{category}'")
    else:
        counts[category] += 1

    # Case-insensitive duplicate detection
    normalized_text = text.casefold()

    if normalized_text and normalized_text in seen:
        errors.append(f"line {i}: duplicate text '{text}'")

    if normalized_text:
        seen.add(normalized_text)

# Print dataset summary
print(f"Rows: {len(rows)}")

for category in sorted(LABELS):
    print(f"  {category:15s} {counts[category]}")

# Check minimum dataset requirements
if len(rows) < MIN_ROWS:
    errors.append(f"Fewer than {MIN_ROWS} rows")

for category in sorted(LABELS):
    if counts[category] < MIN_EXAMPLES_PER_CATEGORY:
        errors.append(
            f"{category} has fewer than "
            f"{MIN_EXAMPLES_PER_CATEGORY} examples"
        )

# Report validation results
if errors:
    print("\nPROBLEMS:")

    for error in errors[:30]:
        print(" -", error)

    if len(errors) > 30:
        print(f" ... and {len(errors) - 30} more problems")

    sys.exit(1)

print("\nOK - dataset is valid.")
