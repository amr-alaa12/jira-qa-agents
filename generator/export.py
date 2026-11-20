from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path
from typing import Any, List, Mapping, Optional, Sequence, Union

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


def to_playwright_python(story_or_cases: Union[Mapping[str, Any], Sequence[Mapping[str, Any]]],
                         test_cases: Optional[Sequence[Mapping[str, Any]]] = None) -> str:
    if test_cases is None and isinstance(story_or_cases, Sequence):
        cases = story_or_cases
    else:
        cases = test_cases or []

    lines = [
        "from __future__ import annotations",
        "",
        "import pytest",
        "from playwright.sync_api import Page, expect",
        "",
    ]
    for tc in cases:
        tc_id = str(tc.get("id") or "TC").replace("-", "_").lower()
        title = str(tc.get("title") or "test_case")
        safe_title = re.sub(r"[^a-zA-Z0-9_]+", "_", title).strip("_").lower()
        fn_name = f"test_{tc_id}_{safe_title}"
        if len(fn_name) > 80:
            fn_name = fn_name[:80].rstrip("_")

        category = str(tc.get("type") or "functional")
        input_desc = str(tc.get("input") or "")
        expected_desc = str(tc.get("expected") or "")

        lines.append(f"def {fn_name}(page: Page) -> None:")
        lines.append(f'    """{title}')
        lines.append(f"    Category: {category}")
        lines.append(f"    Input: {input_desc}")
        lines.append(f"    Expected: {expected_desc}")
        lines.append('    """')

        steps = list(tc.get("steps") or [])
        for step in steps:
            for code_line in _step_to_playwright(str(step)):
                lines.append(f"    {code_line}")

        for code_line in _expected_to_playwright(expected_desc):
            lines.append(f"    {code_line}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _step_to_playwright(step: str) -> List[str]:
    m_open = re.match(r"^open\s+the\s+(?P<page>.+)$", step, re.IGNORECASE)
    if m_open:
        slug = re.sub(r"[^a-z0-9]+", "-", m_open.group("page").lower()).strip("-")
        return [f'page.goto("/{{{slug}}}")']

    m_fill = re.match(r'^enter\s+(?:the\s+registered\s+\w+\s+|the\s+valid\s+\w+\s+|the\s+\w+\s+)?(?:input\s+|probe\s+)?["\'](?P<val>[^"\']+)["\']\s+in\s+the\s+(?P<fld>.+?)(?:\s+field)?$', step, re.IGNORECASE)
    if m_fill:
        fld = re.sub(r"[^a-z0-9]+", "-", m_fill.group("fld").lower()).strip("-")
        val = m_fill.group("val").replace("\\", "\\\\").replace('"', '\\"')
        return [f'page.locator(\'[name="{fld}"], [data-testid="{fld}"]\').fill("{val}")']

    m_empty = re.match(r"^leave\s+(?:the\s+)?(?P<fld>.+?)(?:\s+field)?\s+empty$", step, re.IGNORECASE)
    if m_empty:
        fld = re.sub(r"[^a-z0-9]+", "-", m_empty.group("fld").lower()).strip("-")
        return [f'page.locator(\'[name="{fld}"], [data-testid="{fld}"]\').fill("")']

    m_login = re.match(r"^log\s+in\s+as\s+[^(]+\((?P<email>[^)]+)\)$", step, re.IGNORECASE)
    if m_login:
        email = m_login.group("email").strip()
        return [
            f'page.locator(\'[name="email"], input[type="email"]\').fill("{email}")',
            'page.locator(\'button[type="submit"]\').click()',
        ]

    m_click = re.match(r"^click\s+(?P<btn>.+)$", step, re.IGNORECASE)
    if m_click:
        btn = m_click.group("btn").strip()
        return [f'page.get_by_role("button", name="{btn}").click()']

    if re.search(r"\bsubmit\b", step, re.IGNORECASE):
        return ['page.locator(\'button[type="submit"], [data-testid="submit"]\').click()']

    return ['page.wait_for_timeout(100)']


def _expected_to_playwright(expected: str) -> List[str]:
    lowered = expected.lower()
    if any(k in lowered for k in ("reject", "error", "denied", "blocked", "not submitted", "invalid")):
        return ['expect(page.locator(".error, [role=\'alert\'], .validation-message")).to_be_visible()']
    if any(k in lowered for k in ("accept", "success", "confirm", "granted", "submitted")):
        return ['expect(page.locator(".success, [role=\'status\'], .confirmation")).to_be_visible()']
    clean = re.sub(r'["\']', '', expected[:35]).strip()
    return [f'expect(page.locator("body")).to_contain_text("{clean}")']


def to_cypress_ts(story_or_cases: Union[Mapping[str, Any], Sequence[Mapping[str, Any]]],
                 test_cases: Optional[Sequence[Mapping[str, Any]]] = None) -> str:
    if test_cases is None and isinstance(story_or_cases, Sequence):
        story: Mapping[str, Any] = {"key": "SUITE", "title": "Automated Test Suite"}
        cases = story_or_cases
    else:
        story = story_or_cases if isinstance(story_or_cases, Mapping) else {}
        cases = test_cases or []

    story_key = str(story.get("key") or "SUITE")
    story_title = str(story.get("title") or "Feature Test Suite")

    lines = [
        f"describe('{story_key}: {story_title}', () => {{",
    ]
    for tc in cases:
        tc_id = str(tc.get("id") or "TC")
        title = str(tc.get("title") or "test case").replace("'", "\\'")
        lines.append(f"  it('{tc_id}: {title}', () => {{")

        steps = list(tc.get("steps") or [])
        for step in steps:
            for code_line in _step_to_cypress(str(step)):
                lines.append(f"    {code_line}")

        expected_desc = str(tc.get("expected") or "")
        for code_line in _expected_to_cypress(expected_desc):
            lines.append(f"    {code_line}")
        lines.append("  });")
        lines.append("")

    lines.append("});")
    return "\n".join(lines).rstrip() + "\n"


def _step_to_cypress(step: str) -> List[str]:
    m_open = re.match(r"^open\s+the\s+(?P<page>.+)$", step, re.IGNORECASE)
    if m_open:
        slug = re.sub(r"[^a-z0-9]+", "-", m_open.group("page").lower()).strip("-")
        return [f'cy.visit("/{{{slug}}}");']

    m_fill = re.match(r'^enter\s+(?:the\s+registered\s+\w+\s+|the\s+valid\s+\w+\s+|the\s+\w+\s+)?(?:input\s+|probe\s+)?["\'](?P<val>[^"\']+)["\']\s+in\s+the\s+(?P<fld>.+?)(?:\s+field)?$', step, re.IGNORECASE)
    if m_fill:
        fld = re.sub(r"[^a-z0-9]+", "-", m_fill.group("fld").lower()).strip("-")
        val = m_fill.group("val").replace("\\", "\\\\").replace("'", "\\'")
        return [f'cy.get(\'[name="{fld}"], [data-testid="{fld}"]\').type(\'{val}\');']

    m_empty = re.match(r"^leave\s+(?:the\s+)?(?P<fld>.+?)(?:\s+field)?\s+empty$", step, re.IGNORECASE)
    if m_empty:
        fld = re.sub(r"[^a-z0-9]+", "-", m_empty.group("fld").lower()).strip("-")
        return [f'cy.get(\'[name="{fld}"], [data-testid="{fld}"]\').clear();']

    m_login = re.match(r"^log\s+in\s+as\s+[^(]+\((?P<email>[^)]+)\)$", step, re.IGNORECASE)
    if m_login:
        email = m_login.group("email").strip()
        return [
            f'cy.get(\'[name="email"], input[type="email"]\').type(\'{email}\');',
            'cy.get(\'button[type="submit"]\').click();',
        ]

    m_click = re.match(r"^click\s+(?P<btn>.+)$", step, re.IGNORECASE)
    if m_click:
        btn = m_click.group("btn").strip().replace("'", "\\'")
        return [f'cy.contains("button", \'{btn}\').click();']

    if re.search(r"\bsubmit\b", step, re.IGNORECASE):
        return ['cy.get(\'button[type="submit"], [data-testid="submit"]\').click();']

    return ['cy.wait(100);']


def _expected_to_cypress(expected: str) -> List[str]:
    lowered = expected.lower()
    if any(k in lowered for k in ("reject", "error", "denied", "blocked", "not submitted", "invalid")):
        return ['cy.get(".error, [role=\'alert\'], .validation-message").should("be.visible");']
    if any(k in lowered for k in ("accept", "success", "confirm", "granted", "submitted")):
        return ['cy.get(".success, [role=\'status\'], .confirmation").should("be.visible");']
    clean = re.sub(r'["\']', '', expected[:35]).strip()
    return [f'cy.get("body").should("contain.text", "{clean}");']

