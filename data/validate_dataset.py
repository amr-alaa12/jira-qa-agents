
import csv
import os
import sys
from collections import Counter

PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "requirements.csv"
)

EXPECTED_COLUMNS = ["project_id", "text", "category", "source"]

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

# Read and validate the CSV structure
with open(PATH, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)

    if reader.fieldnames != EXPECTED_COLUMNS:
        errors.append(
            f"Columns must be exactly {','.join(EXPECTED_COLUMNS)} "
            f"- got {reader.fieldnames}"
        )

    rows = list(reader)

# Validate each row exactly once
counts = Counter()
seen = set()

for i, row in enumerate(rows, start=2):
    project_id = (row.get("project_id") or "").strip()
    text = (row.get("text") or "").strip()
    category = (row.get("category") or "").strip()
    source = (row.get("source") or "").strip()

    if not project_id:
        errors.append(f"line {i}: empty project_id")

    if not text:
        errors.append(f"line {i}: empty text")

    if not source:
        errors.append(f"line {i}: empty source")

    if category not in LABELS:
        errors.append(f"line {i}: bad category '{category}'")
    else:
        counts[category] += 1

    normalized_text = text.lower()

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

# Report validation results once
if errors:
    print("\nPROBLEMS:")
    for error in errors[:30]:
        print(" -", error)

    if len(errors) > 30:
        print(f" ... and {len(errors) - 30} more problems")

    sys.exit(1)

print("\nOK - dataset is valid.")
```
