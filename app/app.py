
import json
from pathlib import Path

import streamlit as st

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


def predict_demo_category(criterion: str) -> str:
    """Simple mock predictions for the frontend demonstration."""
    text = criterion.lower()

    rules = [
        (["8 characters", "at least", "maximum", "minimum", "limit"],
         "boundary"),
        (["valid email", "empty", "invalid", "required", "rejected"],
         "validation"),
        (["securely", "authenticated", "unauthorized", "owner"],
         "security"),
        (["under", "seconds", "response time", "fast"],
         "performance"),
        (["helpful", "easy", "clear", "understand"],
         "usability"),
    ]

    for keywords, category in rules:
        if any(word in text for word in keywords):
            return category

    return "functional"


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
    """Prefer available local stories; otherwise use sample data."""
    root = Path(__file__).resolve().parent.parent

    candidates = [
        root / "examples" / "stories.json",
        root / "data" / "stories.json",
        root / "stories.json",
    ]

    for candidate in candidates:
        stories = load_json_stories(candidate)

        if stories:
            return stories, f"Loaded from {candidate.name}"

    return SAMPLE_STORIES, "Using built-in sample stories"


def generate_demo_cases(story, classified_criteria):
    """Generate illustrative test cases for the demo."""
    cases = []

    def add_case(category, title, steps, expected):
        cases.append({
            "story_key": story["key"],
            "id": f'{story["key"]}-TC{len(cases) + 1}',
            "title": title,
            "type": category,
            "steps": steps,
            "expected": expected,
        })

    for item in classified_criteria:
        criterion = item["criterion"]
        category = item["category"]

        if category == "boundary":
            add_case(
                category,
                f"Value below the minimum: {criterion}",
                [
                    "Open the relevant page",
                    "Enter a value below the required minimum",
                    "Submit the form",
                ],
                "The application rejects the value and displays an error.",
            )
            add_case(
                category,
                f"Value at the minimum: {criterion}",
                [
                    "Open the relevant page",
                    "Enter a value at the required minimum",
                    "Submit the form",
                ],
                "The application accepts the value if other rules are satisfied.",
            )

        elif category == "validation":
            add_case(
                category,
                f"Invalid input is rejected: {criterion}",
                [
                    "Open the relevant page",
                    "Enter invalid or missing data",
                    "Submit the form",
                ],
                f"The application handles invalid input for: {criterion}",
            )

        elif category == "security":
            add_case(
                category,
                f"Access control is enforced: {criterion}",
                [
                    "Attempt the action without valid authorization",
                    "Review the result",
                ],
                "The application prevents unauthorized access.",
            )

        elif category == "performance":
            add_case(
                category,
                f"Performance requirement: {criterion}",
                [
                    "Perform the relevant action",
                    "Measure the response time",
                ],
                "The operation meets the specified performance limit.",
            )

        elif category == "usability":
            add_case(
                category,
                f"Helpful feedback: {criterion}",
                [
                    "Perform the relevant action",
                    "Review the displayed message",
                ],
                "The message is clear and helpful to the user.",
            )

        else:
            add_case(
                category,
                f"Verify requirement: {criterion}",
                [
                    "Open the relevant page",
                    f"Perform the action described by: {criterion}",
                ],
                f"The application satisfies the requirement: {criterion}",
            )

    return cases


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
    category = predict_demo_category(criterion)

    classified_criteria.append({
        "criterion": criterion,
        "category": category,
    })

    with st.container(border=True):
        left, right = st.columns([5, 2])

        left.write(f"**{index}.** {criterion}")
        right.markdown(f"**Category:** `{category}`")


# ---------------- GENERATE TEST CASES ----------------

st.divider()
st.subheader("Generate Test Cases")

st.caption(
    "This frontend demonstration uses sample category predictions "
    "and illustrative test cases. It does not call the real classifier "
    "or generator."
)

if st.button("🧪 Generate Test Cases", type="primary"):
    st.session_state.generated_cases = generate_demo_cases(
        story,
        classified_criteria,
    )
    st.session_state.generated_story_key = story["key"]


# ---------------- DISPLAY RESULTS ----------------

generated_cases = st.session_state.generated_cases

if generated_cases:
    st.success(
        f"{len(generated_cases)} sample test case(s) generated."
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
        "Click Generate Test Cases to preview the workflow."
    )

# ---------------- DEMO STATUS ----------------

with st.expander("About this demonstration"):
    st.write("Stories are loaded from local JSON files when available.")
    st.write("Otherwise, the app uses built-in sample stories.")
    st.write("Category predictions use simple demonstration rules.")
    st.write("Test cases are illustrative and are not generated by an AI model.")

