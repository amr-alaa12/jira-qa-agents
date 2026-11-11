"""Print the Jira custom fields that look like an Acceptance Criteria field.

Usage:  python jira/list_fields.py
Put the printed ID (for example customfield_10035) in JIRA_AC_FIELD in .env.
"""
import sys
from pathlib import Path

import requests
from requests.auth import HTTPBasicAuth

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from jira.fetch import setting  # noqa: E402  (also loads .env)


def main():
    base_url = setting("JIRA_BASE_URL").rstrip("/")
    email = setting("JIRA_EMAIL")
    token = setting("JIRA_API_TOKEN")
    if not all([base_url, email, token]):
        raise SystemExit("Missing JIRA_BASE_URL, JIRA_EMAIL or JIRA_API_TOKEN.")

    try:
        response = requests.get(f"{base_url}/rest/api/3/field", auth=HTTPBasicAuth(email, token),
                                headers={"Accept": "application/json"}, timeout=30)
    except requests.RequestException as exc:
        raise SystemExit(f"Could not contact Jira: {exc}")
    if response.status_code == 401:
        raise SystemExit("Login failed. Check your Jira email and API token.")
    if response.status_code == 403:
        raise SystemExit("Jira denied access to the fields API.")
    response.raise_for_status()

    custom = [field for field in response.json() if field.get("custom")]
    matches = [field for field in custom
               if "acceptance" in field.get("name", "").lower()
               and "criteria" in field.get("name", "").lower()]
    if matches:
        print("Custom fields related to acceptance criteria:\n")
        for field in matches:
            print(f"Name: {field['name']}\nID:   {field['id']}\n")
    else:
        print("No matching custom field found. Available custom fields:")
        for field in custom:
            print(f"{field['name']} -> {field['id']}")


if __name__ == "__main__":
    main()
