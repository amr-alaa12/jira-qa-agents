import joblib
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, 'ai_classifier_model.pkl')
VEC_PATH = os.path.join(BASE_DIR, 'tfidf_vectorizer.pkl')

print("Loading saved model and vectorizer...")
classifier_model = joblib.load(MODEL_PATH)
vectorizer = joblib.load(VEC_PATH)

criteria_list = [
    "Given a valid Jira API token, the system must successfully authenticate and fetch a list of available projects.",
    "When a user inputs a specific Jira issue ID, the system must retrieve the issue's title and description.",
    "If the retrieved Jira issue does not contain any acceptance criteria, the system must display a 'No acceptance criteria found' warning.",
    "The system must support fetching user stories from Jira Cloud instances via the REST API v3.",
    "If the Jira API returns a 401 Unauthorized error, the system must prompt the user to check their environment variables.",
    "The AI classifier must return exactly one of the nine predefined categories for each input criterion.",
    "The AI classifier must attach a confidence score (between 0.0 and 1.0) to every predicted category.",
    "If the text input is completely empty or contains only special characters, the classifier must flag it as invalid rather than guessing.",
    "The classifier must be able to process an array of 50 acceptance criteria in under 5 seconds.",
    "The AI model must correctly identify SQL injection prevention requirements under the 'security' category.",
    "The generator must output every test case in JSON format containing 'title', 'input', and 'expected_output' fields.",
    "When the AI classifier assigns the 'performance' category, the test generator must use the specific performance testing template.",
    "If a user story exceeds 2000 words, the system must truncate it or process it in chunks to avoid context window limits.",
    "If the generator fails to produce a valid 'expected_output', it must insert the placeholder text 'Manual review required'.",
    "The entire pipeline, from Jira fetch to test generation, must complete within a 300-second execution window.",
    "The Streamlit dashboard must display a dropdown menu of fetched Jira stories for user selection.",
    "When a story is selected, the UI must display a loading spinner while the AI processes the requirements.",
    "The generated test cases must be rendered on the dashboard in a readable layout that explicitly shows the 'input' and 'expected_output' fields.",
    "The UI must include a 'Download' button that exports the generated test cases as a formatted Python/Playwright script file.",
    "The application must not log or expose the Jira API token in any console output or error message."
]

print("\nStarting Classifier Evaluation across all 9 categories...\n")

vec_criteria = vectorizer.transform(criteria_list)
preds = classifier_model.predict(vec_criteria)
probs = classifier_model.predict_proba(vec_criteria)

for i, (crit, pred, prob) in enumerate(zip(criteria_list, preds, probs), 1):
    conf = max(prob)
    print("-" * 60)
    print(f"Criterion {i}: {crit}")
    print(f"Predicted Category: {pred}")
    print(f"Confidence Score: {conf:.2f}")
    print("Manual Check (Is this correct?): _________ \n")
print("-" * 60)