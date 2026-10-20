
import json
from pathlib import Path

import streamlit as st

from model.train_and_predict import predict_category
from generator.core import generate_test_cases
from jira.fetch import fetch_stories

st.set_page_config(
    page_title="Jira QA Agents",
    page_icon="🧪",
    layout="wide",
)

CATEGORIES = [
    "functional",
    "validation",
    "boundary",
    "security",
    "performance",
    "usability",
]

SAMPLE_STORIES = [
    {
        "key": "SHOP-1",
        "title": "Reset password",
        "description": (
            "As a user, I want to reset my password "
            "so that I can log in again."
        ),
        "acceptance_criteria": [
            "The user receives a reset link by email",
            "The new password must be at least 8 characters",
        ],
    },
    {
        "key": "SHOP-2",
        "title": "User login",
        "description": (
            "As a registered user, I want to log in "
            "securely to access my account."
        ),
        "acceptance_criteria": [
            "Users must enter a valid email address",
            "Incorrect passwords must be rejected",
            "Only authenticated users can access their account",
        ],
    },
    {
        "key": "SHOP-3",
        "title": "Product search",
        "description": (
            "As a customer, I want to search for products by name."
        ),
        "acceptance_criteria": [
            "Search results must match the entered product name",
            "An empty search must show a helpful message",
        ],
    },
]





def load_json_stories(path: Path):
    """Load stories from a local JSON file."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))

        if isinstance(data, list):
            return [
                item for item in data
                if isinstance(item, dict) and item.get("key")
            ]
    except (OSError, json.JSONDecodeError):
        pass

    return []


def get_stories():
    """Fetch Jira stories, with local and sample fallbacks."""
    root = Path(__file__).resolve().parent.parent

    try:
        stories = fetch_stories("KAN")
        if stories:
            return stories, "Connected to Jira project KAN"
    except Exception as error:
        st.warning(f"Could not fetch Jira stories: {error}")

    candidates = [
        root / "stories.json",
        root / "examples" / "stories.json",
        root / "data" / "stories.json",
    ]

    for candidate in candidates:
        stories = load_json_stories(candidate)
        if stories:
            return stories, f"Loaded from {candidate.name}"

    return SAMPLE_STORIES, "Using built-in sample stories"





# ---------------- PAGE HEADER ----------------

st.title("🧪 Jira QA Agents")
st.caption(
    "Turn user stories and acceptance criteria "
    "into categorized test cases."
)

stories, source_label = get_stories()
st.caption(f"Story source: {source_label}")


# ---------------- STORY SELECTION ----------------

story_labels = {
    f'{s["key"]} — {s.get("title", "Untitled story")}': s
    for s in stories
}

if not story_labels:
    st.warning("No stories are available.")
    st.stop()

selected_label = st.selectbox(
    "Select a user story",
    list(story_labels.keys()),
)

story = story_labels[selected_label]

criteria = story.get("acceptance_criteria", [])
if not isinstance(criteria, list):
    criteria = []


# ---------------- DASHBOARD STATISTICS ----------------

if "generated_cases" not in st.session_state:
    st.session_state.generated_cases = []

if "generated_story_key" not in st.session_state:
    st.session_state.generated_story_key = None

if st.session_state.generated_story_key != story["key"]:
    st.session_state.generated_cases = []
    st.session_state.generated_story_key = story["key"]

col1, col2, col3 = st.columns(3)

col1.metric("Stories Available", len(stories))
col2.metric("Acceptance Criteria", len(criteria))
col3.metric(
    "Generated Test Cases",
    len(st.session_state.generated_cases),
)


# ---------------- STORY DETAILS ----------------

st.divider()

st.subheader(f'{story["key"]}: {story.get("title", "Untitled story")}')
st.write(story.get("description", "No description provided."))

st.markdown("### Acceptance Criteria and Predicted Categories")

classified_criteria = []

for index, criterion in enumerate(criteria, start=1):
    criterion = str(criterion)
    category, confidence = predict_category(criterion)

    classified_criteria.append({
        "criterion": criterion,
        "category": category,
    })

    with st.container(border=True):
        left, right = st.columns([5, 2])

        left.write(f"**{index}.** {criterion}")
        right.markdown(f"**Category:** `{category}`")
        right.caption(f"Confidence: {confidence:.0%}")


# ---------------- GENERATE TEST CASES ----------------

st.divider()
st.subheader("Generate Test Cases")

st.caption(
    "Uses the trained requirement classifier and test case generator."
)

if st.button("🧪 Generate Test Cases", type="primary"):
    try:
        categories = [
            predict_category(str(criterion))
            for criterion in criteria
        ]

        st.session_state.generated_cases = generate_test_cases(
            story,
            categories,
        )

        st.session_state.generated_story_key = story["key"]

    except Exception as error:
        st.error(f"Could not generate test cases: {error}")


# ---------------- DISPLAY RESULTS ----------------

generated_cases = st.session_state.generated_cases

if generated_cases:
    st.success(
       f"{len(generated_cases)} test case(s) generated successfully."
    )

    for case in generated_cases:
        with st.expander(
            f'{case["id"]} — {case["title"]}',
            expanded=True,
        ):
            st.markdown(f'**Category:** `{case["type"]}`')
            st.markdown("**Test Steps**")

            for step_index, step in enumerate(case["steps"], start=1):
                st.write(f"{step_index}. {step}")

            st.markdown("**Expected Result**")
            st.write(case["expected"])

    st.download_button(
        "Download Test Cases as JSON",
        data=json.dumps(
            generated_cases,
            indent=2,
            ensure_ascii=False,
        ),
        file_name=f'{story["key"]}_test_cases.json',
        mime="application/json",
    )

else:
   st.info(
    "No test cases generated yet. "
    "Click Generate Test Cases to create them."
)


# ---------------- ABOUT ----------------

with st.expander("About Jira QA Agents"):
    st.write("Stories are loaded from local JSON files when available.")
    st.write("If no local stories are found, built-in sample stories are used.")
    st.write("Acceptance criteria are classified using the trained requirement classifier.")
    st.write("Test cases are generated using the project's test case generator.")

