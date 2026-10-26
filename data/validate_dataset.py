"""Checks data/requirements.csv. Run:  python data/validate_dataset.py"""
import csv, os, sys
from collections import Counter

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.csv")
LABELS = {"functional", "validation", "boundary", "security", "performance", "usability"}
errors = []

with open(PATH, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    if reader.fieldnames != ["text", "category"]:
        errors.append(f"Columns must be exactly text,category - got {reader.fieldnames}")
    rows = list(reader)

counts, seen = Counter(), set()
for i, r in enumerate(rows, start=2):
    text, cat = (r.get("text") or "").strip(), (r.get("category") or "").strip()
    if not text: errors.append(f"line {i}: empty text")
    if cat not in LABELS: errors.append(f"line {i}: bad category '{cat}'")
    if text.lower() in seen: errors.append(f"line {i}: duplicate text '{text}'")
    seen.add(text.lower()); counts[cat] += 1

print(f"Rows: {len(rows)}")
for c in sorted(LABELS): print(f"  {c:12s} {counts[c]}")
if len(rows) < 1000: errors.append("Fewer than 1000 rows")
for c in LABELS:
    if counts[c] < 50: errors.append(f"{c} has fewer than 50 examples")

if errors:
    print("\nPROBLEMS:"); [print(" -", e) for e in errors[:30]]; sys.exit(1)
print("\nOK - dataset is valid.")
