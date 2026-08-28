"""
Usage:
    python predict.py                    # runs 3 built-in demo patients
    python predict.py --json '{"age": 52, "sex": "male", "hemoglobin": 11.0, ...}'
"""
import argparse
import json
import os

import joblib
import numpy as np

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")

DEMO_PATIENTS = {
    "healthy_demo": {
        "age": 29, "sex": "female", "hemoglobin": 13.8, "fasting_glucose": 86,
        "hba1c": 5.1, "ldl": 92, "hdl": 62, "triglycerides": 88, "creatinine": 0.8,
        "alt": 20, "ast": 22, "systolic_bp": 112, "diastolic_bp": 70,
        "heart_rate": 68, "spo2": 99, "bmi": 21.5,
    },
    "moderate_demo": {
        "age": 54, "sex": "male", "hemoglobin": 11.8, "fasting_glucose": 152,
        "hba1c": 6.4, "ldl": 158, "hdl": 38, "triglycerides": 210, "creatinine": 1.1,
        "alt": 40, "ast": 38, "systolic_bp": 138, "diastolic_bp": 88,
        "heart_rate": 84, "spo2": 96, "bmi": 29.0,
    },
    "emergency_demo": {
        "age": 67, "sex": "male", "hemoglobin": 9.5, "fasting_glucose": 420,
        "hba1c": 10.8, "ldl": 190, "hdl": 30, "triglycerides": 310, "creatinine": 2.4,
        "alt": 70, "ast": 65, "systolic_bp": 192, "diastolic_bp": 108,
        "heart_rate": 118, "spo2": 87, "bmi": 33.5,
    },
}


def load_artifacts():
    model = joblib.load(os.path.join(MODEL_DIR, "model.pkl"))
    scaler = joblib.load(os.path.join(MODEL_DIR, "scaler.pkl"))
    with open(os.path.join(MODEL_DIR, "feature_names.json")) as f:
        feature_names = json.load(f)
    return model, scaler, feature_names


def predict_one(model, scaler, feature_names, patient: dict, label: str = "patient"):
    row = dict(patient)
    sex = str(row.pop("sex", "")).lower()
    row["sex_male"] = 1 if sex.startswith("m") else 0

    x = np.array([[row.get(name, 0) for name in feature_names]])
    x_scaled = scaler.transform(x)

    prediction = int(model.predict(x_scaled)[0])
    proba = model.predict_proba(x_scaled)[0]
    probabilities = {int(cls): round(float(p), 3) for cls, p in zip(model.classes_, proba)}

    print(f"\n--- {label} ---")
    print(f"Predicted AEGIS risk level: {prediction}")
    print(f"Class probabilities: {probabilities}")

    if hasattr(model, "coef_"):
        class_idx = list(model.classes_).index(prediction)
        coefs = model.coef_[class_idx] if model.coef_.ndim > 1 else model.coef_[0]
        contributions = x_scaled[0] * coefs
        ranked = sorted(zip(feature_names, contributions), key=lambda t: abs(t[1]), reverse=True)[:5]
        print("Top contributing features:")
        for name, val in ranked:
            direction = "raises" if val > 0 else "lowers"
            print(f"  {name:16s} {direction} predicted risk (weight {val:+.2f})")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", help="Patient as a JSON object; runs built-in demos if omitted")
    args = parser.parse_args()

    if not os.path.exists(os.path.join(MODEL_DIR, "model.pkl")):
        print("No trained model found. Run `python train.py` first.")
        return

    model, scaler, feature_names = load_artifacts()

    if args.json:
        patient = json.loads(args.json)
        predict_one(model, scaler, feature_names, patient, label="custom patient")
    else:
        for label, patient in DEMO_PATIENTS.items():
            predict_one(model, scaler, feature_names, patient, label=label)


if __name__ == "__main__":
    main()
