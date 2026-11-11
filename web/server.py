"""Jira QA Agents — web version for Vercel.

Vercel cannot run Streamlit, so this small Flask app shows the same steps as
app/app.py: choose a story, see the predicted category of each acceptance
criterion, generate test cases with Input and Expected output, download JSON.
It reuses the project's own code (jira/, generator/, model/) without changing it.

Visitors log in with their own Atlassian account (web/atlassian.py) and see only
their own Jira sites and projects. Without logging in, the sample stories are shown.

Run locally:  flask --app web.server run       (then open http://127.0.0.1:5000)
On Vercel:    pyproject.toml points to web.server:app
"""
import json
import os
import secrets
import sys
import time
from functools import lru_cache
from pathlib import Path

from flask import Flask, Response, redirect, render_template, request, session, url_for
from werkzeug.middleware.proxy_fix import ProxyFix

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generator import CategoryModel, generate_test_cases  # noqa: E402
from generator.classifier import LOW_CONFIDENCE  # noqa: E402
from web import atlassian  # noqa: E402

# Same sample stories as app/app.py, shown when nobody is logged in.
SAMPLE_STORIES = [
    {
        "key": "SHOP-1",
        "title": "Reset password",
        "description": "As a user, I want to reset my password so that I can log in again.",
        "acceptance_criteria": [
            "The user receives a reset link by email",
            "The new password must be at least 8 characters",
        ],
    },
    {
        "key": "SHOP-2",
        "title": "User login",
        "description": "As a registered user, I want to log in securely to access my account.",
        "acceptance_criteria": [
            "Users must enter a valid email address",
            "Incorrect passwords must be rejected",
            "Only authenticated users can access their account",
        ],
    },
    {
        "key": "SHOP-3",
        "title": "Product search",
        "description": "As a customer, I want to search for products by name.",
        "acceptance_criteria": [
            "Search results must match the entered product name",
            "An empty search must show a helpful message",
        ],
    },
]

app = Flask(__name__, template_folder=str(Path(__file__).resolve().parent / "templates"))
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)   # Vercel serves over HTTPS through a proxy
app.secret_key = atlassian.secret_key() or None
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                  SESSION_COOKIE_SECURE=os.getenv("VERCEL") == "1")


@lru_cache(maxsize=1)
def load_model():
    """Load model/model.pkl once per server instance."""
    return CategoryModel.load()


# --- login state -------------------------------------------------------------------

def redirect_uri():
    return os.getenv("ATLASSIAN_REDIRECT_URI") or url_for("callback", _external=True)


def logged_in_token():
    """The user's Atlassian token, or None. An expired login is cleared."""
    if not atlassian.is_configured() or "token" not in session:
        return None
    if time.time() > session.get("expires_at", 0):
        session.clear()
        session["notice"] = "Your Atlassian login has expired. Please log in again."
        return None
    try:
        return atlassian.decrypt(session["token"])
    except atlassian.AuthExpired as exc:
        session.clear()
        session["notice"] = str(exc)
        return None


def jira_context(token):
    """Sites, chosen site, projects, chosen project and stories for a logged-in user."""
    sites = atlassian.cached("sites", token, loader=lambda: atlassian.accessible_sites(token))
    if not sites:
        raise PermissionError("Your Atlassian account has no Jira site that this app may read.")
    site = next((s for s in sites if s["id"] == session.get("cloud_id")), sites[0])
    session["cloud_id"] = site["id"]
    projects = atlassian.cached("projects", token, site["id"],
                                loader=lambda: atlassian.list_projects(token, site["id"]))
    wanted = request.args.get("project") or session.get("project") or os.getenv("JIRA_PROJECT_KEY", "")
    project = next((p for p in projects if p["key"] == wanted), projects[0] if projects else None)
    stories = []
    if project:
        session["project"] = project["key"]
        ac_field = os.getenv("JIRA_AC_FIELD", "")
        stories = atlassian.cached("stories", token, site["id"], project["key"],
                                   loader=lambda: atlassian.fetch_stories(token, site["id"], project["key"],
                                                                          ac_field))
    return sites, site, projects, project, stories


def has_session():
    """Flask can only use the login cookie when APP_SECRET_KEY is set."""
    return bool(app.secret_key)


def get_stories():
    """Returns (stories, context dict for the page)."""
    token = logged_in_token()   # first, so a "login expired" notice is shown on this same page
    context = {"configured": atlassian.is_configured(), "user": session.get("user") if has_session() else None,
               "sites": [], "site": None, "projects": [], "project": None,
               "warning": session.pop("notice", None) if has_session() else None}
    if not token:
        context["user"] = None
        return SAMPLE_STORIES, {**context, "source": "Sample stories — log in with Atlassian to see your Jira"}
    try:
        sites, site, projects, project, stories = jira_context(token)
    except atlassian.AuthExpired as exc:
        session.clear()
        return SAMPLE_STORIES, {**context, "user": None, "warning": str(exc), "source": "Sample stories"}
    except (PermissionError, ValueError, OSError) as exc:   # requests errors are OSError subclasses
        return SAMPLE_STORIES, {**context, "warning": f"Could not read Jira: {exc}", "source": "Sample stories"}
    context.update(sites=sites, site=site, projects=projects, project=project)
    if not project:
        context["warning"] = "Your account cannot see any project on this Jira site."
    source = f"Jira site {site['name']}" + (f", project {project['key']}" if project else "")
    return stories, {**context, "source": source}


# --- pages -------------------------------------------------------------------------

def find_story(stories, key):
    return next((story for story in stories if story["key"] == key), stories[0] if stories else None)


def criteria_of(story):
    criteria = (story or {}).get("acceptance_criteria", [])
    return [str(criterion) for criterion in criteria] if isinstance(criteria, list) else []


@app.get("/")
def index():
    stories, context = get_stories()
    story = find_story(stories, request.args.get("story", ""))
    criteria = criteria_of(story)
    predictions = load_model().predict(criteria)
    test_cases, error = [], None
    if story and request.args.get("generate") and criteria:
        try:
            test_cases = generate_test_cases({**story, "acceptance_criteria": criteria}, predictions)
        except ValueError as exc:
            error = f"Could not generate test cases: {exc}"
    return render_template(
        "index.html", stories=stories, story=story, error=error, rows=list(zip(criteria, predictions)),
        test_cases=test_cases, low=LOW_CONFIDENCE, generated=bool(request.args.get("generate")), **context)


@app.get("/download")
def download():
    stories, _ = get_stories()
    story = find_story(stories, request.args.get("story", ""))
    if not story:
        return Response("[]", mimetype="application/json")
    criteria = criteria_of(story)
    test_cases = generate_test_cases({**story, "acceptance_criteria": criteria},
                                     load_model().predict(criteria)) if criteria else []
    return Response(json.dumps(test_cases, indent=2, ensure_ascii=False), mimetype="application/json",
                    headers={"Content-Disposition": f'attachment; filename="{story["key"]}_test_cases.json"'})


@app.get("/privacy")
@app.get("/privacy.html")
def privacy():
    """Public privacy policy, linked from the Atlassian app's Distribution settings."""
    return render_template("privacy.html")


@app.get("/login")
def login():
    if not atlassian.is_configured():
        return redirect(url_for("index"))
    session["oauth_state"] = secrets.token_urlsafe(32)
    return redirect(atlassian.authorize_url(redirect_uri(), session["oauth_state"]))


@app.get("/callback")
def callback():
    if not has_session():
        return redirect(url_for("index"))
    expected = session.pop("oauth_state", None)
    if not atlassian.is_configured() or not expected or request.args.get("state") != expected:
        session["notice"] = "The login could not be verified. Please try again."
        return redirect(url_for("index"))
    if request.args.get("error") or not request.args.get("code"):
        session["notice"] = "The Atlassian login was cancelled."
        return redirect(url_for("index"))
    try:
        token, expires_in = atlassian.exchange_code(request.args["code"], redirect_uri())
        sites = atlassian.accessible_sites(token)
        user = atlassian.current_user(token, sites[0]["id"]) if sites else "Atlassian user"
    except (atlassian.AuthExpired, PermissionError, OSError, KeyError, ValueError) as exc:
        session["notice"] = f"Login failed: {exc}"
        return redirect(url_for("index"))
    session.clear()
    session.update(token=atlassian.encrypt(token), expires_at=time.time() + expires_in - 60, user=user,
                   cloud_id=sites[0]["id"] if sites else None)
    return redirect(url_for("index"))


@app.get("/site")
def choose_site():
    if not has_session():
        return redirect(url_for("index"))
    session["cloud_id"] = request.args.get("cloud_id", "")
    session.pop("project", None)
    return redirect(url_for("index"))


@app.get("/logout")
def logout():
    if has_session():
        session.clear()
    return redirect(url_for("index"))


@app.get("/health")
def health():
    return {"status": "ok", "login_configured": atlassian.is_configured(),
            "model_classes": list(load_model()._classes)}


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG") == "1")
