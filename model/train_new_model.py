import pandas as pd
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import os

# 1. Load dataset from the 'data' folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, '..', 'data', 'requirements_merged_with_dosspre_new.csv')

print("Loading dataset from data folder...")
df = pd.read_csv(CSV_PATH, encoding='latin1')
df = df.dropna(subset=['text', 'category'])

# 2. Include all 9 categories and standardize to uppercase
target_categories = [
    'functional', 'security', 'performance', 'usability', 
    'validation', 'boundary', 'reliability', 'portability', 'maintainability'
]
df_clean = df[df['category'].str.lower().isin(target_categories)].copy()
df_clean['category'] = df_clean['category'].str.upper()

print("Full Dataset Category Distribution (All 9 Categories):")
print(df_clean['category'].value_counts())

# 3. Stratified split to guarantee all 9 categories are present in both train and test sets
X_train, X_test, y_train, y_test = train_test_split(
    df_clean['text'], 
    df_clean['category'], 
    test_size=0.2, 
    random_state=42,
    stratify=df_clean['category']
)

# 4. Vectorizer with N-grams to catch multi-word phrases (like "API token" or "error message")
vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2))
X_train_vec = vectorizer.fit_transform(X_train)
X_test_vec = vectorizer.transform(X_test)

# 5. Tuned Logistic Regression with higher C parameter for sharper decision boundaries
model = LogisticRegression(C=3.0, max_iter=1000, class_weight='balanced')
model.fit(X_train_vec, y_train)

# 6. Evaluate
y_pred = model.predict(X_test_vec)
print("\nModel Evaluation on Test Set:")
print(classification_report(y_test, y_pred))

# 7. Save the model and vectorizer
MODEL_SAVE_PATH = os.path.join(BASE_DIR, 'ai_classifier_model.pkl')
VEC_SAVE_PATH = os.path.join(BASE_DIR, 'tfidf_vectorizer.pkl')

joblib.dump(model, MODEL_SAVE_PATH)
joblib.dump(vectorizer, VEC_SAVE_PATH)

print(f"\nSuccess! Updated 9-category model saved to {MODEL_SAVE_PATH}")