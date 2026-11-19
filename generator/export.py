from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any, Mapping, Sequence, Union

from .text import to_gherkin


def to_csv(test_cases: Sequence[Mapping[str, Any]]) -> str:
    output = io.StringIO()
    if not test_cases:
        return ""
    has_optional = any("priority" in tc for tc in test_cases)
    fields = ["Story Key", "Test ID", "Title", "Type", "Input", "Steps", "Expected Result"]
    if has_optional:
        fields.extend(["Priority", "Preconditions", "Execution Type", "Gherkin"])
    writer = csv.writer(output)
    writer.writerow(fields)
    for tc in test_cases:
        steps_text = "\n".join(f"{i+1}. {step}" for i, step in enumerate(tc.get("steps") or []))
        row = [
            str(tc.get("story_key", "")),
            str(tc.get("id", "")),
            str(tc.get("title", "")),
            str(tc.get("type", "")),
            str(tc.get("input", "")),
            steps_text,
            str(tc.get("expected", "")),
        ]
        if has_optional:
            preconditions = "\n".join(f"- {p}" for p in (tc.get("preconditions") or []))
            row.extend([
                str(tc.get("priority", "")),
                preconditions,
                str(tc.get("execution_type", "")),
                str(tc.get("gherkin", "")),
            ])
        writer.writerow(row)
    return output.getvalue()


def to_excel(test_cases: Sequence[Mapping[str, Any]], output_path: Union[str, Path]) -> None:
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Test Cases"

    has_optional = any("priority" in tc for tc in test_cases)
    headers = ["Story Key", "Test ID", "Title", "Type", "Input", "Steps", "Expected Result"]
    if has_optional:
        headers.extend(["Priority", "Preconditions", "Execution Type"])

    ws.append(headers)
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for tc in test_cases:
        steps_text = "\n".join(f"{i+1}. {s}" for i, s in enumerate(tc.get("steps") or []))
        row = [
            str(tc.get("story_key", "")),
            str(tc.get("id", "")),
            str(tc.get("title", "")),
            str(tc.get("type", "")),
            str(tc.get("input", "")),
            steps_text,
            str(tc.get("expected", "")),
        ]
        if has_optional:
            preconditions = "\n".join(f"- {p}" for p in (tc.get("preconditions") or []))
            row.extend([
                str(tc.get("priority", "")),
                preconditions,
                str(tc.get("execution_type", "")),
            ])
        ws.append(row)

    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=len(headers)):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")

    column_widths = [12, 14, 30, 14, 25, 40, 35]
    if has_optional:
        column_widths.extend([12, 30, 15])
    for i, width in enumerate(column_widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = width

    path_obj = Path(output_path)
    if path_obj.parent:
        path_obj.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)


def to_gherkin_feature(story: Mapping[str, Any], test_cases: Sequence[Mapping[str, Any]]) -> str:
    title = str(story.get("title") or story.get("key") or "Feature")
    desc = str(story.get("description") or "").strip()
    lines = [f"Feature: {title}"]
    if desc:
        for desc_line in desc.splitlines():
            lines.append(f"  {desc_line.strip()}")
        lines.append("")
    for tc in test_cases:
        lines.append(to_gherkin(tc))
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def to_xray_json(test_cases: Sequence[Mapping[str, Any]]) -> str:
    tests = []
    for tc in test_cases:
        steps_list = list(tc.get("steps") or [])
        steps = [
            {
                "action": s,
                "result": tc.get("expected") if i == len(steps_list) - 1 else "",
            }
            for i, s in enumerate(steps_list)
        ]
        tests.append({
            "testKey": tc.get("id"),
            "info": {
                "summary": tc.get("title"),
                "type": "Manual" if tc.get("execution_type") == "manual" else "Automated",
                "priority": tc.get("priority", "Medium"),
                "requirementKeys": [tc.get("story_key")],
                "labels": [str(tc.get("type"))],
            },
            "steps": steps,
        })
    return json.dumps({"tests": tests}, indent=2)
