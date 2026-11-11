# Jira QA Agents

Takes a Jira user story and its acceptance criteria, classifies each criterion into one of six
categories (functional, validation, boundary, security, performance, usability) and generates
test cases that state their **input** and **expected output**.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                     # fill JIRA_EMAIL and JIRA_API_TOKEN
streamlit run app/app.py
```

Without Jira credentials the app still runs: it uses `stories.json`, then
`examples/stories.json`, then built-in sample stories.

## Web version (Vercel)

Vercel cannot run Streamlit, so `web/server.py` is a small Flask version of the same app
(same steps, same generator and classifier). `pyproject.toml` tells Vercel to use it.
Live: https://jira-qa-agents.vercel.app

```bash
flask --app web.server run               # http://127.0.0.1:5000
```

Visitors **log in with their own Atlassian account** and see only their own Jira sites and
projects (read-only). Without logging in, the sample stories are shown.

### Set up the Atlassian login

1. At https://developer.atlassian.com/console/myapps/ create an **OAuth 2.0 integration**.
2. **Permissions** → Jira API → add the scopes `read:jira-work` and `read:jira-user`.
3. **Authorization** → OAuth 2.0 (3LO) → callback URL `https://jira-qa-agents.vercel.app/callback`.
4. **Settings** → copy the Client ID and Secret.
5. In Vercel → project → Settings → Environment Variables, add:

| Variable | Value |
|---|---|
| `ATLASSIAN_CLIENT_ID` | the Client ID |
| `ATLASSIAN_CLIENT_SECRET` | the Secret |
| `APP_SECRET_KEY` | a long random string (protects the login cookie) |
| `ATLASSIAN_REDIRECT_URI` | `https://jira-qa-agents.vercel.app/callback` |
| `JIRA_PROJECT_KEY` | optional: project shown first, e.g. `KAN` |

Then redeploy. To let people outside your team log in, set the app's **Distribution** to
"Sharing" in the developer console.

## Command line

```bash
python jira/fetch.py KAN                 # Jira -> stories.json
python jira/list_fields.py               # find the ID of an "Acceptance Criteria" custom field
python model/train_new_model.py          # data/ -> model/model.pkl
python generator/generate.py stories.json --output test_cases.json
python data/validate_dataset.py          # check data/requirements.csv
python -m pytest -q                      # all tests
```

## Project structure

| Folder | What it does | Owner |
|---|---|---|
| `app/` | Streamlit app | Moataz |
| `web/` | web version of the app for Vercel (Flask) | Moataz |
| `jira/` | Jira REST connector | Amr |
| `data/` | datasets and validation | Omar |
| `model/` | requirement classifier | Ahmed |
| `generator/` | test-case generator and its tests | Zayd |
| `examples/` | sample stories and test cases | — |
| `tests/` | tests that cover several modules | Amr |
| `docs/` | prototype, comparison and research notes | Amr |

## Test-case format

```json
{
  "story_key": "SHOP-1",
  "id": "SHOP-1-TC4",
  "title": "New password with 7 characters is rejected",
  "type": "boundary",
  "input": "New password: \"Passw0r\" (7 characters)",
  "steps": ["Open the reset password page", "Enter \"Passw0r\" (7 characters) in the new password field", "Submit the form"],
  "expected_output": "The new password is rejected, the form is not submitted and an error message explains the limit (at least 8 characters)"
}
```

## Configuration

Settings are read from Streamlit secrets when deployed, otherwise from `.env`
(see `.env.example`): `JIRA_BASE_URL`, `JIRA_PROJECT_KEY`, `JIRA_EMAIL`,
`JIRA_API_TOKEN` and, optionally, `JIRA_AC_FIELD`. Never commit `.env`.

# Vision
**A Multi-Agent LLM Framework for Automated UI Test Generation and Self-Healing**

## Project Overview

Jira QA Agents is a research project exploring the use of Large Language Models (LLMs) and multi-agent systems to automate the software UI testing lifecycle.

The proposed framework transforms Jira user stories and acceptance criteria into executable UI test scripts, evaluates test failures, and investigates self-healing techniques to improve test robustness as web applications evolve.

## Research Objectives

- **Requirements Analysis:** Extract user stories and acceptance criteria from Jira and identify ambiguity or quality issues.
- **Requirements Classification:** Classify requirements as Functional Requirements (FR) or Non-Functional Requirements (NFR), including relevant quality attributes.
- **Test Case Generation:** Generate structured test cases from user stories and acceptance criteria using LLM-based agents.
- **Test Script Generation:** Convert generated test cases into executable UI automation scripts using Playwright and Python.
- **Multi-Agent Orchestration:** Investigate how specialized AI agents can collaborate to generate, review, and improve test artifacts.
- **Failure Analysis:** Analyze execution failures to distinguish potential locator issues from other test or application failures.
- **Self-Healing UI Tests:** Investigate techniques for identifying replacement UI elements and repairing broken locators.
- **Evaluation:** Measure test-generation quality, execution success, repair accuracy, and overall framework performance.

## Proposed Workflow

1. Retrieve user stories and acceptance criteria from Jira.
2. Analyze requirements quality and detect ambiguity.
3. Classify requirements and identify relevant quality attributes.
4. Generate test cases from acceptance criteria.
5. Generate executable Playwright test scripts.
6. Execute tests and collect results.
7. Analyze failures and investigate possible locator repairs.
8. Re-run repaired tests and evaluate the results.

## Planned Technology Stack

- **Programming Language:** Python
- **Artificial Intelligence:** Large Language Models (LLMs)
- **Architecture:** Multi-agent system
- **Requirements Source:** Jira REST API
- **UI Automation:** Playwright
- **Test Framework:** pytest
- **Version Control:** Git and GitHub

Specific libraries and orchestration frameworks will be selected as the implementation develops.

## Research and Evaluation

The project will investigate the following evaluation dimensions:

- Accuracy and completeness of generated test cases.
- Traceability between acceptance criteria and generated tests.
- Executable test-script success rate.
- Comparison between single-agent and multi-agent approaches.
- Accuracy of failure classification and locator repair.
- Test recovery rate after UI changes.
- Limitations, reliability, and reproducibility of LLM-generated artifacts.

Evaluation methods and baselines will be defined during the research process.

## Literature Review

The research draws on existing work in:

- User story quality assessment and requirements engineering.
- Functional and non-functional requirements classification.
- LLM-based test case and test script generation.
- Multi-agent LLM orchestration for software engineering.
- Self-healing locators and automated web test repair.

Relevant papers, implementation notes, and experimental findings will be documented throughout the project.

