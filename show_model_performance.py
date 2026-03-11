import joblib
from sklearn.metrics import classification_report

model = joblib.load("models/best_model.pkl")
X_test = joblib.load("data/processed/X_test.pkl")
y_test = joblib.load("data/processed/y_test.pkl")

y_pred = model.predict(X_test)

print(classification_report(
    y_test,
    y_pred,
    target_names=["Legitimate", "Fraud"]
))