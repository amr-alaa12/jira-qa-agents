
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


def adf_to_text(value):
    """Convert Jira's Atlassian Document Format into readable text."""
    if isinstance(value, str):
        return value

    if isinstance(value, list):
        return "\n".join(
            text for item in value
            if (text := adf_to_text(item))
        )

    if isinstance(value, dict):
        if value.get("type") == "text":
            return value.get("text", "")

        parts = []
        for child in value.get("content", []):
            text = adf_to_text(child)
            if text:
                parts.append(text)

        result = "\n".join(parts)

        if value.get("type") in ("bulletList", "orderedList"):
            return "\n".join(f"- {part}" for part in parts)

        return result

    return ""


def extract_criteria(description):
    """Extract acceptance criteria from a description heading."""
    text = adf_to_text(description)
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    criteria = []
    collecting = False

    for line in lines:
        clean_line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip()

        if re.match(r"^acceptance\s+criteria\s*:?\s*$", clean_line, re.I):
            collecting = True
            continue

        if collecting:
            if re.match(
                r"^(description|attachments|comments|"
                r"definition of done|notes|steps)\s*:?\s*$",
                clean_line,
                re.I,
            ):
                break

            clean_line = re.sub(r"^\[[ xX]\]\s*", "", clean_line)

            if clean_line:
                criteria.append(clean_line)

    return criteria


def fetch_stories(project_key):
    """Fetch Jira issues and save them using the agreed JSON schema."""
    base_url = os.getenv("JIRA_BASE_URL", "").rstrip("/")
    email = os.getenv("JIRA_EMAIL", "")
    token = os.getenv("JIRA_API_TOKEN", "")
    ac_field = os.getenv("JIRA_AC_FIELD", "").strip()

    if not all([base_url, email, token]):
        raise ValueError(
            "Missing JIRA_BASE_URL, JIRA_EMAIL, or JIRA_API_TOKEN "
            "in your local .env file."
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
            f"Project '{project_key}' was not found or is not accessible."
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

    output_path = ROOT / "stories.json"

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(stories, file, indent=2, ensure_ascii=False)

    print(f"Fetched {len(stories)} issues from project {project_key}.")
    print(f"Saved output to: {output_path}")

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
        fetch_stories(sys.argv[1])
    except (
        requests.RequestException,
        RuntimeError,
        ValueError,
    ) as exc:
        raise SystemExit(f"Jira connector error: {exc}")
