import json
import os
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


# ADF nodes that hold text on one line. Their children are joined with "" (not "\n"),
# so "must be **at least 8** characters" stays one sentence.
INLINE_PARENTS = {"paragraph", "heading", "tableCell", "tableHeader"}


def adf_to_text(value):
    """Convert Jira's Atlassian Document Format into readable text."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(text for item in value if (text := adf_to_text(item)))
    if not isinstance(value, dict):
        return ""

    node_type = value.get("type")
    if node_type == "text":
        return value.get("text", "")
    if node_type == "hardBreak":
        return " "
    if node_type in ("mention", "emoji", "date", "status"):
        return str(value.get("attrs", {}).get("text", ""))
    if node_type == "inlineCard":
        return str(value.get("attrs", {}).get("url", ""))

    children = [adf_to_text(child) for child in value.get("content", [])]
    if node_type in INLINE_PARENTS:
        return re.sub(r"\s+", " ", "".join(children)).strip()
    parts = [part for part in children if part]
    if node_type in ("bulletList", "orderedList"):
        return "\n".join(f"- {part}" for part in parts)
    return "\n".join(parts)


_AC_HEADING_RE = re.compile(r"^acceptance\s+criteria\s*:?\s*$", re.I)
_AC_INLINE_RE = re.compile(r"\bacceptance\s+criteria\s*:\s*(?P<rest>.*)$", re.I)
_END_HEADING_RE = re.compile(
    r"^(description|attachments|comments|definition of done|notes|steps)\s*:?\s*$", re.I)
_NUMBER_RE = re.compile(r"(?:^|(?<=\s))(\d{1,2})[.)]\s+")


def split_numbered(text):
    """Split "1. First rule. 2. Second rule." written on one line into separate rules.

    Only a run 1, 2, 3, ... counts, so "within 2. seconds" or "version 3. x" alone do not split.
    """
    starts, expected = [], 1
    for match in _NUMBER_RE.finditer(text):
        if int(match.group(1)) == expected:
            starts.append(match)
            expected += 1
    if len(starts) < 2:
        return [text]
    parts = [text[:starts[0].start()]]
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        parts.append(text[match.end():end])
    return [part.strip() for part in parts if part.strip()]


def _clean(line):
    line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip()
    return re.sub(r"^\[[ xX]\]\s*", "", line).strip()


def extract_criteria(description):
    """Extract acceptance criteria from a description.

    Works with an "Acceptance Criteria" heading followed by one rule per line, and with
    "Acceptance Criteria: 1. ... 2. ..." written inside a paragraph.
    """
    text = adf_to_text(description)
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    criteria = []
    collecting = False

    for line in lines:
        clean_line = _clean(line)

        if _AC_HEADING_RE.match(clean_line):
            collecting = True
            continue

        if not collecting:
            inline = _AC_INLINE_RE.search(line)
            if inline:
                collecting = True
                line = inline.group("rest")
                if not line.strip():
                    continue
            else:
                continue

        if _END_HEADING_RE.match(clean_line):
            break

        for part in split_numbered(line):
            part = _clean(part)
            if part:
                criteria.append(part)

    return criteria


def setting(name):
    """Read a setting from Streamlit secrets when deployed, otherwise from .env."""
    try:
        import streamlit as st              # optional: the CLI works without Streamlit
        value = st.secrets.get(name)
    except Exception:                       # no Streamlit, or no secrets file
        value = None
    return str(value if value is not None else os.getenv(name, "")).strip()


def save_stories(stories, path=ROOT / "stories.json"):
    """Write stories to stories.json (used by the command line only)."""
    with Path(path).open("w", encoding="utf-8") as file:
        json.dump(stories, file, indent=2, ensure_ascii=False)
    return path


def fetch_stories(project_key):
    
    """Fetch Jira issues and save them using the agreed JSON schema."""
 
    base_url = setting("JIRA_BASE_URL").rstrip("/")
    email = setting("JIRA_EMAIL")
    token = setting("JIRA_API_TOKEN")
    ac_field = setting("JIRA_AC_FIELD")
    if not all([base_url, email, token]):
        raise ValueError(
            "Missing JIRA_BASE_URL, JIRA_EMAIL, or JIRA_API_TOKEN "
            "(set them in .env locally or in Streamlit secrets when deployed)."
        )

    fields = ["summary", "description", "issuetype"]

    if re.fullmatch(r"customfield_\d+", ac_field):
        fields.append(ac_field)

    session = requests.Session()
    session.auth = HTTPBasicAuth(email, token)
    session.headers.update({"Accept": "application/json"})

    # Verify that the project exists and is accessible.
    project_response = session.get(
        f"{base_url}/rest/api/3/project/{project_key}",
        timeout=30,
    )

    if project_response.status_code == 401:
        raise RuntimeError(
            "Jira authentication failed. Check your email and API token."
        )

    if project_response.status_code == 403:
        raise RuntimeError("Jira denied access to this project.")

    if project_response.status_code == 404:
        raise RuntimeError(
        f"Jira returned 404 for project '{project_key}'. "
        f"Response: {project_response.text[:500]}"
    )

    project_response.raise_for_status()

    stories = []
    next_page_token = None

    while True:
        # Fetch all issue types, not only issues of type Story.
        payload = {
            "jql": f'project = "{project_key}" ORDER BY created DESC',
            "fields": fields,
            "maxResults": 100,
        }

        if next_page_token:
            payload["nextPageToken"] = next_page_token

        response = session.post(
            f"{base_url}/rest/api/3/search/jql",
            json=payload,
            timeout=60,
        )

        if response.status_code == 401:
            raise RuntimeError(
                "Jira authentication failed during issue search."
            )

        if response.status_code == 403:
            raise RuntimeError(
                "You do not have permission to search these Jira issues."
            )

        response.raise_for_status()
        data = response.json()

        for issue in data.get("issues", []):
            issue_fields = issue.get("fields", {})
            description = issue_fields.get("description")

            criteria = []

            # Use a configured custom field if one is identified.
            if ac_field and ac_field in issue_fields:
                raw_criteria = issue_fields.get(ac_field)

                if isinstance(raw_criteria, list):
                    criteria = [
                        adf_to_text(item).strip()
                        for item in raw_criteria
                        if adf_to_text(item).strip()
                    ]
                elif raw_criteria:
                    text = adf_to_text(raw_criteria).strip()
                    if text:
                        criteria = [text]

            # Otherwise, extract criteria from the description.
            if not criteria:
                criteria = extract_criteria(description)

            stories.append({
                "key": issue["key"],
                "title": issue_fields.get("summary", ""),
                "description": adf_to_text(description),
                "acceptance_criteria": criteria,
            })

        next_page_token = data.get("nextPageToken")

        if not next_page_token:
            break

    print(f"Fetched {len(stories)} issues from project {project_key}.")

    if not stories:
        print("No issues were found in this project.")

    missing_criteria = [
        story["key"]
        for story in stories
        if not story["acceptance_criteria"]
    ]

    if missing_criteria:
        print(
            "No acceptance criteria extracted for: "
            + ", ".join(missing_criteria)
        )
        print(
            "Check whether these issues have an Acceptance Criteria "
            "heading in their descriptions."
        )

    return stories


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python jira/fetch.py PROJECT_KEY")

    try:
        output_path = save_stories(fetch_stories(sys.argv[1]))
        print(f"Saved output to: {output_path}")
    except (
        requests.RequestException,
        RuntimeError,
        ValueError,
    ) as exc:
        raise SystemExit(f"Jira connector error: {exc}")
