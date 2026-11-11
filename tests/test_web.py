"""Tests for the Vercel web version (web/server.py) and the Atlassian login (web/atlassian.py)."""
import json
import sys
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from web import atlassian, server  # noqa: E402

TOKEN = "user-access-token-123"
CLOUD = "cloud-1"


def adf(*parts):
    return {"type": "paragraph", "content": list(parts)}


def text(value, **extra):
    return {"type": "text", "text": value, **extra}


DESCRIPTION = {"type": "doc", "content": [
    adf(text("As a user, I want to reset my password.")),
    {"type": "heading", "content": [text("Acceptance Criteria")]},
    {"type": "bulletList", "content": [{"type": "listItem", "content": [
        adf(text("The new password must be "), text("at least 8", marks=[{"type": "strong"}]), text(" characters"))]}]},
]}


class FakeResponse:
    def __init__(self, status, data):
        self.status_code, self._data = status, data

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise atlassian.requests.HTTPError(str(self.status_code))


class FakeAtlassian:
    """Answers the Atlassian and Jira endpoints the app calls."""

    def __init__(self):
        self.calls, self.expired = [], False

    def post(self, url, json=None, timeout=None, headers=None):
        self.calls.append(("POST", url, json))
        if url == atlassian.TOKEN_URL:
            ok = json["code"] == "good-code" and json["client_secret"] == "secret"
            return FakeResponse(200 if ok else 400, {"access_token": TOKEN, "expires_in": 3600})
        if url.endswith("/rest/api/3/search/jql"):
            if self.expired:
                return FakeResponse(401, {})
            assert headers["Authorization"] == f"Bearer {TOKEN}"
            assert json["jql"] == 'project = "KAN" ORDER BY created DESC'
            return FakeResponse(200, {"issues": [
                {"key": "KAN-1", "fields": {"summary": "Reset password", "description": DESCRIPTION}},
                {"key": "KAN-2", "fields": {"summary": "Fix crash", "description": None}},
            ]})
        raise AssertionError(url)

    def get(self, url, params=None, timeout=None, headers=None):
        self.calls.append(("GET", url, params))
        assert headers["Authorization"] == f"Bearer {TOKEN}"
        if self.expired:
            return FakeResponse(401, {})
        if url == atlassian.RESOURCES_URL:
            return FakeResponse(200, [{"id": CLOUD, "name": "miuegypt-team", "url": "https://x.atlassian.net"}])
        if url.endswith("/rest/api/3/myself"):
            return FakeResponse(200, {"displayName": "Ali Test"})
        if url.endswith("/rest/api/3/project/search"):
            return FakeResponse(200, {"values": [{"key": "KAN", "name": "Graduation"}], "isLast": True})
        raise AssertionError(url)


@pytest.fixture
def fake(monkeypatch):
    fake = FakeAtlassian()
    monkeypatch.setattr(atlassian.requests, "post", fake.post)
    monkeypatch.setattr(atlassian.requests, "get", fake.get)
    monkeypatch.setattr(atlassian, "_cache", {})
    return fake


@pytest.fixture
def configured(monkeypatch, fake):
    monkeypatch.setenv("ATLASSIAN_CLIENT_ID", "client")
    monkeypatch.setenv("ATLASSIAN_CLIENT_SECRET", "secret")
    monkeypatch.setenv("APP_SECRET_KEY", "a-long-random-test-key")
    monkeypatch.setenv("JIRA_PROJECT_KEY", "KAN")
    monkeypatch.setattr(server.app, "secret_key", "a-long-random-test-key")
    return server.app.test_client()


@pytest.fixture
def anonymous(monkeypatch):
    for name in ("ATLASSIAN_CLIENT_ID", "ATLASSIAN_CLIENT_SECRET", "APP_SECRET_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(server.app, "secret_key", None)
    return server.app.test_client()


def log_in(client):
    redirect = client.get("/login")
    query = parse_qs(urlparse(redirect.headers["Location"]).query)
    return client.get(f"/callback?code=good-code&state={query['state'][0]}"), query


# --- without login -----------------------------------------------------------------

def test_without_login_setup_the_samples_work(anonymous):
    page = anonymous.get("/?story=SHOP-2&generate=1").get_data(as_text=True)
    assert "Atlassian login is not set up" in page
    assert "test case(s) ready for SHOP-2" in page
    assert page.count("<strong>Expected output</strong>") == page.count("<strong>Input</strong>") > 0
    assert "Not provided" not in page


def test_routes_do_not_crash_without_a_secret_key(anonymous):
    for path in ("/login", "/callback?code=x&state=y", "/logout", "/site?cloud_id=x"):
        assert anonymous.get(path).status_code == 302


def test_download_returns_the_agreed_format(anonymous):
    response = anonymous.get("/download?story=SHOP-1")
    assert response.headers["Content-Disposition"] == 'attachment; filename="SHOP-1_test_cases.json"'
    cases = json.loads(response.get_data(as_text=True))
    assert cases and all({"input", "expected_output", "steps", "title"} <= set(case) for case in cases)


def test_text_is_escaped(anonymous, monkeypatch):
    monkeypatch.setattr(server, "SAMPLE_STORIES", [
        {"key": "X-1", "title": "<script>alert(1)</script>", "acceptance_criteria": ["The name is required"]}])
    page = anonymous.get("/?generate=1").get_data(as_text=True)
    assert "<script>alert(1)</script>" not in page and "&lt;script&gt;" in page


def test_logged_out_visitor_sees_the_login_button(configured):
    page = configured.get("/").get_data(as_text=True)
    assert "Log in with Atlassian" in page and "Sample stories" in page


# --- login flow --------------------------------------------------------------------

def test_login_redirects_to_atlassian_with_read_only_scopes(configured):
    response = configured.get("/login")
    url = urlparse(response.headers["Location"])
    query = parse_qs(url.query)
    assert f"{url.scheme}://{url.netloc}{url.path}" == atlassian.AUTHORIZE_URL
    assert query["audience"] == ["api.atlassian.com"] and query["client_id"] == ["client"]
    assert query["scope"] == ["read:jira-work read:jira-user"]
    assert query["response_type"] == ["code"] and query["prompt"] == ["consent"]
    assert query["redirect_uri"] == ["http://localhost/callback"]
    assert len(query["state"][0]) >= 32


def test_full_login_shows_the_users_own_jira(configured, fake):
    response, _ = log_in(configured)
    assert response.status_code == 302
    page = configured.get("/?story=KAN-1&generate=1").get_data(as_text=True)
    assert "Logged in as <strong>Ali Test</strong>" in page and "miuegypt-team" in page
    assert "KAN - Graduation" in page and "Jira site miuegypt-team, project KAN" in page
    assert "The new password must be at least 8 characters" in page      # criterion kept whole
    assert "test case(s) ready for KAN-1" in page


def test_token_is_encrypted_in_the_cookie(configured):
    log_in(configured)
    cookie = configured.get_cookie("session")
    assert cookie and TOKEN not in cookie.value


def test_story_without_criteria_shows_a_message(configured):
    log_in(configured)
    page = configured.get("/?story=KAN-2&generate=1").get_data(as_text=True)
    assert "has no acceptance criteria" in page


def test_jira_is_cached_between_clicks(configured, fake):
    log_in(configured)
    configured.get("/?story=KAN-1")
    configured.get("/?story=KAN-1&generate=1")
    assert sum(1 for call in fake.calls if call[1].endswith("/search/jql")) == 1


def test_wrong_state_is_rejected(configured, fake):
    configured.get("/login")
    configured.get("/callback?code=good-code&state=forged")
    assert not any(call[1] == atlassian.TOKEN_URL for call in fake.calls)
    assert "could not be verified" in configured.get("/").get_data(as_text=True)


def test_bad_code_shows_an_error(configured):
    redirect = configured.get("/login")
    state = parse_qs(urlparse(redirect.headers["Location"]).query)["state"][0]
    configured.get(f"/callback?code=bad-code&state={state}")
    assert "Login failed" in configured.get("/").get_data(as_text=True)


def test_cancelled_login(configured):
    redirect = configured.get("/login")
    state = parse_qs(urlparse(redirect.headers["Location"]).query)["state"][0]
    configured.get(f"/callback?error=access_denied&state={state}")
    assert "was cancelled" in configured.get("/").get_data(as_text=True)


def test_expired_token_logs_the_user_out(configured, fake):
    log_in(configured)
    fake.expired = True
    atlassian._cache.clear()
    page = configured.get("/").get_data(as_text=True)
    assert "expired" in page and "Log in with Atlassian" in page


def test_expiry_time_is_enforced(configured, monkeypatch):
    log_in(configured)
    real_time = time.time
    monkeypatch.setattr(server.time, "time", lambda: real_time() + 4000)
    page = configured.get("/").get_data(as_text=True)
    assert "has expired" in page and "Log in with Atlassian" in page


def test_logout(configured):
    log_in(configured)
    configured.get("/logout")
    assert "Log in with Atlassian" in configured.get("/").get_data(as_text=True)


def test_invalid_project_key_is_refused():
    with pytest.raises(ValueError):
        atlassian.fetch_stories(TOKEN, CLOUD, 'KAN" OR project = "SECRET')


def test_health(anonymous):
    data = anonymous.get("/health").get_json()
    assert data["login_configured"] is False
    assert sorted(data["model_classes"]) == [
        "boundary", "functional", "performance", "security", "usability", "validation"]
