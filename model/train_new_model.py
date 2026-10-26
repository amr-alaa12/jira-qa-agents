import pandas as pd
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import os

# 1. Load dataset
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, 'requirements_merged_with_dosspre_new.csv')

print("Loading dataset...")
df = pd.read_csv(CSV_PATH, encoding='latin1')
df = df.dropna(subset=['text', 'category'])

# 2. Filter out unwanted categories and standardize to uppercase
target_categories = ['functional', 'security', 'performance', 'usability', 'validation', 'boundary']
df_clean = df[df['category'].str.lower().isin(target_categories)].copy()
df_clean['category'] = df_clean['category'].str.upper()

print("Final Category Distribution:")
print(df_clean['category'].value_counts())

# 3. Split the data (80% training, 20% testing)
X_train, X_test, y_train, y_test = train_test_split(
    df_clean['text'], 
    df_clean['category'], 
    test_size=0.2, 
    random_state=42
)

# 4. Vectorize the text
vectorizer = TfidfVectorizer(stop_words='english')
X_train_vec = vectorizer.fit_transform(X_train)
X_test_vec = vectorizer.transform(X_test)

# 5. Train the Model
model = LogisticRegression(max_iter=1000, class_weight='balanced')
model.fit(X_train_vec, y_train)

# 6. Evaluate
y_pred = model.predict(X_test_vec)
print("\nModel Evaluation on 20% Test Split:")
print(classification_report(y_test, y_pred))

# 7. Save the model and vectorizer
MODEL_SAVE_PATH = os.path.join(BASE_DIR, 'ai_classifier_model.pkl')
VEC_SAVE_PATH = os.path.join(BASE_DIR, 'tfidf_vectorizer.pkl')

joblib.dump(model, MODEL_SAVE_PATH)
joblib.dump(vectorizer, VEC_SAVE_PATH)

print(f"\nSuccess! Model saved to {MODEL_SAVE_PATH}")