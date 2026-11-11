"""Log in with Atlassian (OAuth 2.0 three-legged) and read the user's own Jira stories.

Each visitor logs in with their own Atlassian account, so the app only sees the
Jira sites and projects that person can see. The text parsing (ADF and the
"Acceptance Criteria" section) reuses jira/fetch.py unchanged.

Docs: https://developer.atlassian.com/cloud/jira/platform/oauth-2-3lo-apps/
"""
import base64
import hashlib
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlencode

import requests
from cryptography.fernet import Fernet, InvalidToken

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from jira.fetch import adf_to_text, extract_criteria  # noqa: E402

AUTHORIZE_URL = "https://auth.atlassian.com/authorize"
TOKEN_URL = "https://auth.atlassian.com/oauth/token"
RESOURCES_URL = "https://api.atlassian.com/oauth/token/accessible-resources"
API_BASE = "https://api.atlassian.com/ex/jira/{cloud_id}"
# Read-only: issues and projects (read:jira-work), the user's name (read:jira-user).
SCOPES = "read:jira-work read:jira-user"
TIMEOUT = 30


class AuthExpired(Exception):
    """The Atlassian login is no longer valid; the user must log in again."""


def client_id():
    return os.getenv("ATLASSIAN_CLIENT_ID", "").strip()


def client_secret():
    return os.getenv("ATLASSIAN_CLIENT_SECRET", "").strip()


def secret_key():
    return os.getenv("APP_SECRET_KEY", "").strip()


def is_configured():
    """Login needs the Atlassian app's ID and secret, and a key to protect the login cookie."""
    return bool(client_id() and client_secret() and secret_key())


# --- encrypted token in the session cookie ------------------------------------------

def _fernet():
    digest = hashlib.sha256(("atlassian-token:" + secret_key()).encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt(token):
    return _fernet().encrypt(token.encode()).decode()


def decrypt(value):
    try:
        return _fernet().decrypt(value.encode()).decode()
    except (InvalidToken, ValueError, AttributeError):
        raise AuthExpired("Your login could not be read. Please log in again.") from None


# --- OAuth flow --------------------------------------------------------------------

def authorize_url(redirect_uri, state):
    return AUTHORIZE_URL + "?" + urlencode({
        "audience": "api.atlassian.com",
        "client_id": client_id(),
        "scope": SCOPES,
        "redirect_uri": redirect_uri,
        "state": state,
        "response_type": "code",
        "prompt": "consent",
    })


def exchange_code(code, redirect_uri):
    """Swap the one-time code from the callback for an access token."""
    response = requests.post(TOKEN_URL, json={
        "grant_type": "authorization_code",
        "client_id": client_id(),
        "client_secret": client_secret(),
        "code": code,
        "redirect_uri": redirect_uri,
    }, timeout=TIMEOUT)
    if response.status_code != 200:
        raise AuthExpired("Atlassian did not accept the login. Please try again.")
    data = response.json()
    return data["access_token"], int(data.get("expires_in", 3600))


def accessible_sites(token):
    """The Jira sites this user allowed the app to read: [{"id", "name", "url"}, ...]."""
    data = _get(RESOURCES_URL, token)
    return [{"id": site["id"], "name": site.get("name", site["id"]), "url": site.get("url", "")}
            for site in data if site.get("id")]


# --- Jira REST API with the user's token --------------------------------------------

def _get(url, token, params=None):
    response = requests.get(url, params=params, timeout=TIMEOUT, headers={
        "Authorization": f"Bearer {token}", "Accept": "application/json"})
    return _check(response)


def _check(response):
    if response.status_code == 401:
        raise AuthExpired("Your Atlassian login has expired. Please log in again.")
    if response.status_code == 403:
        raise PermissionError("Your Atlassian account cannot read this Jira site or project.")
    response.raise_for_status()
    return response.json()


def current_user(token, cloud_id):
    data = _get(API_BASE.format(cloud_id=cloud_id) + "/rest/api/3/myself", token)
    return data.get("displayName") or data.get("emailAddress") or "Atlassian user"


def list_projects(token, cloud_id):
    """Projects the user can browse on this site: [{"key", "name"}, ...] sorted by name."""
    projects, start = [], 0
    while True:
        data = _get(API_BASE.format(cloud_id=cloud_id) + "/rest/api/3/project/search", token,
                    {"startAt": start, "maxResults": 50, "orderBy": "name"})
        projects += [{"key": p["key"], "name": p.get("name", p["key"])} for p in data.get("values", [])]
        if data.get("isLast", True) or not data.get("values"):
            return projects
        start += len(data["values"])


def fetch_stories(token, cloud_id, project_key, ac_field=""):
    """Stories in the same format as jira/fetch.py: key, title, description, acceptance_criteria."""
    if not re.fullmatch(r"[A-Z][A-Z0-9_]*", project_key or ""):
        raise ValueError(f"Invalid project key: {project_key!r}")
    fields = ["summary", "description", "issuetype"]
    if re.fullmatch(r"customfield_\d+", ac_field):
        fields.append(ac_field)

    url = API_BASE.format(cloud_id=cloud_id) + "/rest/api/3/search/jql"
    stories, next_page = [], None
    while True:
        payload = {"jql": f'project = "{project_key}" ORDER BY created DESC', "fields": fields, "maxResults": 100}
        if next_page:
            payload["nextPageToken"] = next_page
        data = _check(requests.post(url, json=payload, timeout=60, headers={
            "Authorization": f"Bearer {token}", "Accept": "application/json"}))
        for issue in data.get("issues", []):
            issue_fields = issue.get("fields", {})
            description = issue_fields.get("description")
            criteria = []
            raw = issue_fields.get(ac_field) if ac_field else None
            if isinstance(raw, list):
                criteria = [text for item in raw if (text := adf_to_text(item).strip())]
            elif raw:
                text = adf_to_text(raw).strip()
                criteria = [text] if text else []
            if not criteria:
                criteria = extract_criteria(description)
            stories.append({"key": issue["key"], "title": issue_fields.get("summary", ""),
                            "description": adf_to_text(description), "acceptance_criteria": criteria})
        next_page = data.get("nextPageToken")
        if not next_page:
            return stories


# --- small per-instance cache so every click does not call Jira again ---------------

_cache = {}
CACHE_SECONDS = 60


def cached(kind, token, *args, loader):
    key = (kind, hashlib.sha256(token.encode()).hexdigest(), *args)
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1]
    value = loader()
    if len(_cache) > 500:
        _cache.clear()
    _cache[key] = (time.time(), value)
    return value
