import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score
import joblib
import os

def predict_category(sentence):
    """Loads the saved model and predicts the category of a given sentence."""
    saved_model = joblib.load('model/model.pkl')
    category = saved_model.predict([sentence])[0]
    probs = saved_model.predict_proba([sentence])[0]
    confidence = max(probs)
    return category, round(confidence, 2)

def train_model():
    """Downloads the dataset, trains the model, evaluates it, and saves it."""
    # 1. Read the dataset directly from Member 2's branch
    github_csv_url = "https://raw.githubusercontent.com/amr-alaa12/jira-qa-agents/dataset-builder/data/requirements.csv"
    
    print(f"Loading training data from: {github_csv_url}")
    try:
        df = pd.read_csv(github_csv_url)
    except Exception as e:
        # Fallback to local file
        print(f"Could not download directly ({e}), checking local path...")
        df = pd.read_csv("data/requirements.csv")
        
    print(f"Successfully loaded {len(df)} rows.")

    # 2. Split data: 80% train, 20% test
    X_train, X_test, y_train, y_test = train_test_split(
        df['text'], df['category'], test_size=0.2, random_state=42
    )

    # 3. Create pipeline (TF-IDF Vectorizer + Logistic Regression)
    model_pipeline = Pipeline([
        ('vectorizer', TfidfVectorizer()),
        ('classifier', LogisticRegression(max_iter=1000))
    ])

    # 4. Train the model
    print("Training the classifier...")
    model_pipeline.fit(X_train, y_train)

    # 5. Evaluate accuracy
    y_pred = model_pipeline.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Model Accuracy: {accuracy * 100:.2f}%\n")

    # 6. Save model to model/model.pkl
    os.makedirs('model', exist_ok=True)
    joblib.dump(model_pipeline, 'model/model.pkl')
    print("Model saved to model/model.pkl\n")

# This block ensures training ONLY happens when you run the file directly
if __name__ == "__main__":
    # Execute the training function
    train_model()
    
    # Test the prediction function to verify it still works
    test_input = "The page loads in under 2 seconds"
    cat, conf = predict_category(test_input)
    print("--- Prediction Test ---")
    print(f"Sentence: '{test_input}'")
    print(f"Predicted Category: {cat}")
    print(f"Confidence: {conf}")