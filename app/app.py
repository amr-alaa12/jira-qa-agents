import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st

from model.train_and_predict import predict_category
from generator.core import generate_test_cases
from jira.fetch import fetch_stories

st.set_page_config(page_title="Jira QA Agents", page_icon="🧪", layout="wide")

st.markdown(
    """
    <style>
    :root {
        --ink: #202c3b;
        --muted: #5e6c7d;
        --line: #e3e8ef;
        --surface: #ffffff;
    --accent: #2459a6;
    --accent-hover: #194785;
    }
    .stApp { background: #f4f6f9; color: var(--ink); }
    [data-testid="stHeader"] { background: rgba(244, 246, 249, 0.96); }
    .block-container { max-width: 1080px; padding-top: 2.6rem; padding-bottom: 4rem; }
    h1, h2, h3, h4 { color: var(--ink); letter-spacing: -0.025em; }
    h1 { font-size: 2.35rem; font-weight: 700; }
    p, label, .stCaption { color: var(--muted); line-height: 1.6; }
    [data-testid="stVerticalBlockBorderWrapper"], [data-testid="stExpander"] {
        background: var(--surface); border: 1px solid var(--line); border-radius: 14px;
        box-shadow: 0 2px 8px rgba(32, 44, 59, 0.035);
    }
    [data-testid="stExpander"] summary { color: var(--ink); font-weight: 600; }
    [data-testid="stBaseButton-primary"], .stButton > button[kind="primary"] {
        background: var(--accent) !important; border: 1px solid var(--accent) !important;
        color: #fff !important; border-radius: 10px !important; min-height: 2.8rem;
        font-weight: 600 !important; box-shadow: 0 2px 5px rgba(41, 75, 112, 0.16);
    }
    [data-testid="stBaseButton-primary"] *, .stButton > button[kind="primary"] * {
        color: #ffffff !important;
    }
    [data-testid="stBaseButton-primary"]:hover, .stButton > button[kind="primary"]:hover {
        background: var(--accent-hover) !important; border-color: var(--accent-hover) !important;
    }
    [data-testid="stBaseButton-secondary"], .stDownloadButton button {
        background: #fff !important; border: 1px solid #cbd5e1 !important;
        color: #34465b !important; border-radius: 10px !important; min-height: 2.6rem;
    }
    [data-testid="stBaseButton-secondary"]:hover, .stDownloadButton button:hover {
        background: #eef2f7 !important; border-color: #9eacbd !important;
    }
    [data-testid="stSelectbox"] > div > div {
        background: #fff; border-radius: 10px; border-color: #d7dee8;
    }
    [data-testid="stSelectbox"] [data-baseweb="select"] {
        background: #ffffff !important;
        color: var(--ink) !important;
    }
    [data-testid="stSelectbox"] [data-baseweb="select"] * {
        color: var(--ink) !important;
    }
    [data-testid="stAlert"] { border-radius: 12px; }
    hr { border-color: var(--line); }
    </style>
    """,
    unsafe_allow_html=True,
)

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


def load_json_stories(path: Path):
    """Load stories from a local JSON file."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict) and item.get("key")]
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

    for candidate in (root / "stories.json", root / "examples" / "stories.json", root / "data" / "stories.json"):
        stories = load_json_stories(candidate)
        if stories:
            return stories, f"Loaded from {candidate.name}"
    return SAMPLE_STORIES, "Using built-in sample stories"


st.title("Jira QA Agents")
st.caption(
    "Choose a Jira story, review its acceptance criteria, "
    "then generate test cases with clear inputs and expected outputs."
)
stories, source_label = get_stories()
st.caption(f"Stories: {len(stories)} | Source: {source_label}")

story_labels = {
    f'{item["key"]} - {item.get("title", "Untitled story")}': item
    for item in stories
}
if not story_labels:
    st.warning("No stories are available.")
    st.stop()

st.markdown("### 1. Choose a story")
selected_label = st.selectbox("User story", list(story_labels.keys()))
story = story_labels[selected_label]
criteria = story.get("acceptance_criteria", [])
if not isinstance(criteria, list):
    criteria = []

if "generated_cases" not in st.session_state:
    st.session_state.generated_cases = []
if "generated_story_key" not in st.session_state:
    st.session_state.generated_story_key = None
if st.session_state.generated_story_key != story["key"]:
    st.session_state.generated_cases = []
    st.session_state.generated_story_key = story["key"]

st.divider()
st.markdown("### 2. Review the story")
st.subheader(f'{story["key"]}: {story.get("title", "Untitled story")}')
st.write(story.get("description") or "No description provided.")
st.markdown("#### Acceptance criteria")
st.caption("The predicted category helps determine which test cases are created.")

for index, criterion in enumerate(criteria, start=1):
    criterion = str(criterion)
    category, confidence = predict_category(criterion)
    with st.container(border=True):
        left, right = st.columns([5, 2])
        left.write(f"**{index}.** {criterion}")
        right.markdown(f"**Predicted category:** `{category}`")
        right.caption(f"Confidence: {confidence:.0%}")

st.divider()
st.markdown("### 3. Generate test cases")
st.caption("Create test cases from this story's acceptance criteria.")
if st.button("Generate test cases", type="primary", use_container_width=True):
    try:
        with st.spinner("Generating test cases..."):
            categories = [predict_category(str(criterion)) for criterion in criteria]
            st.session_state.generated_cases = generate_test_cases(story, categories)
            st.session_state.generated_story_key = story["key"]
    except Exception as error:
        st.error(f"Could not generate test cases: {error}")

generated_cases = st.session_state.generated_cases
if generated_cases:
    st.divider()
    st.markdown("### Your test cases")
    st.success(f"{len(generated_cases)} test case(s) ready for {story['key']}.")
    st.caption("Open a case to review its input, steps, and expected output.")
    for case in generated_cases:
        with st.expander(
            f'{case.get("id", "Test case")} - {case.get("title", "Untitled test case")}',
            expanded=False,
        ):
            st.caption(f'Category: {case.get("type", "Not specified")}')
            input_col, expected_col = st.columns(2)
            with input_col:
                st.markdown("**Input**")
                st.write(case.get("input") or "Not provided")
            with expected_col:
                st.markdown("**Expected output**")
                st.write(case.get("expected") or "Not provided")
            st.markdown("**Steps**")
            steps = case.get("steps") or []
            if steps:
                for step_index, step in enumerate(steps, start=1):
                    st.write(f"{step_index}. {step}")
            else:
                st.caption("No steps provided.")

    st.download_button(
        "Download test cases as JSON",
        data=json.dumps(generated_cases, indent=2, ensure_ascii=False),
        file_name=f'{story["key"]}_test_cases.json',
        mime="application/json",
    )
else:
    st.info("No test cases yet. Select a story, then choose **Generate test cases**.")

with st.expander("About Jira QA Agents"):
    st.write("Stories are loaded from local JSON files when available.")
    st.write("If no local stories are found, built-in sample stories are used.")
    st.write("Acceptance criteria are classified using the trained requirement classifier.")
    st.write("Test cases are generated using the project's test case generator.")
