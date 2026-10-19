
import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

base_url = os.getenv("JIRA_BASE_URL", "").rstrip("/")
email = os.getenv("JIRA_EMAIL", "")
token = os.getenv("JIRA_API_TOKEN", "")

if not all([base_url, email, token]):
    raise SystemExit("Missing Jira settings in your local .env file.")

try:
    response = requests.get(
        f"{base_url}/rest/api/3/field",
        auth=HTTPBasicAuth(email, token),
        headers={"Accept": "application/json"},
        timeout=30,
    )

    if response.status_code == 401:
        raise SystemExit("Login failed. Check your Jira email and API token.")
    if response.status_code == 403:
        raise SystemExit("Jira denied access to the fields API.")

    response.raise_for_status()

    fields = response.json()
    print("Custom fields related to acceptance criteria:\n")

    matches = [
        field for field in fields
        if field.get("custom")
        and "acceptance" in field.get("name", "").lower()
        and "criteria" in field.get("name", "").lower()
    ]

    if matches:
        for field in matches:
            print(f"Name: {field['name']}")
            print(f"ID:   {field['id']}\n")
    else:
        print("No matching custom field found.")
        print("Available custom fields:")
        for field in fields:
            if field.get("custom"):
                print(f"{field['name']} -> {field['id']}")

except requests.RequestException as exc:
    print(f"Could not contact Jira: {exc}")
