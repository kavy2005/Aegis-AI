"""
Trains the AEGIS AI baseline risk-level classifier.

Usage:
    python train.py                # logistic regression baseline (default)
    python train.py --model rf     # random forest alternative

Split discipline: 60/20/20 train/val/test, stratified by target, with a
fixed random_state for reproducibility. The scaler is fit on TRAIN ONLY and
reused (never refit) on val/test to avoid leakage. The exact split is saved
to disk (train.csv/val.csv/test.csv) so evaluate.py always scores against
the identical held-out test set this script produced, not a fresh re-split.
"""
import argparse
import json
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
os.makedirs(MODEL_DIR, exist_ok=True)

FEATURE_COLUMNS = [
    "age", "sex_male", "hemoglobin", "fasting_glucose", "hba1c", "ldl", "hdl",
    "triglycerides", "creatinine", "alt", "ast", "systolic_bp", "diastolic_bp",
    "heart_rate", "spo2", "bmi",
]


def load_dataset():
    df = pd.read_csv(os.path.join(DATA_DIR, "synthetic_patients.csv"))
    df["sex_male"] = (df["sex"] == "male").astype(int)
    return df


def split_and_save(df):
    train_df, temp_df = train_test_split(
        df, test_size=0.4, stratify=df["target"], random_state=42
    )
    val_df, test_df = train_test_split(
        temp_df, test_size=0.5, stratify=temp_df["target"], random_state=42
    )
    train_df.to_csv(os.path.join(DATA_DIR, "train.csv"), index=False)
    val_df.to_csv(os.path.join(DATA_DIR, "val.csv"), index=False)
    test_df.to_csv(os.path.join(DATA_DIR, "test.csv"), index=False)
    return train_df, val_df, test_df


def build_model(kind):
    if kind == "rf":
        return RandomForestClassifier(n_estimators=200, max_depth=8, random_state=42)
    return LogisticRegression(max_iter=2000, random_state=42)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=["logreg", "rf"], default="logreg")
    args = parser.parse_args()

    df = load_dataset()
    train_df, val_df, test_df = split_and_save(df)
    print(f"Split: train={len(train_df)} val={len(val_df)} test={len(test_df)}")

    X_train = train_df[FEATURE_COLUMNS].values
    y_train = train_df["target"].values
    X_val = val_df[FEATURE_COLUMNS].values
    y_val = val_df["target"].values

    scaler = StandardScaler().fit(X_train)
    X_train_scaled = scaler.transform(X_train)
    X_val_scaled = scaler.transform(X_val)

    model = build_model(args.model)
    model.fit(X_train_scaled, y_train)

    val_pred = model.predict(X_val_scaled)
    val_accuracy = accuracy_score(y_val, val_pred)
    print(f"Model: {args.model} | Validation accuracy: {val_accuracy:.3f}")

    joblib.dump(model, os.path.join(MODEL_DIR, "model.pkl"))
    joblib.dump(scaler, os.path.join(MODEL_DIR, "scaler.pkl"))
    with open(os.path.join(MODEL_DIR, "feature_names.json"), "w") as f:
        json.dump(FEATURE_COLUMNS, f, indent=2)
    with open(os.path.join(MODEL_DIR, "metrics.json"), "w") as f:
        json.dump({
            "model_type": args.model,
            "train_size": len(train_df),
            "val_size": len(val_df),
            "test_size": len(test_df),
            "val_accuracy": round(float(val_accuracy), 4),
            "features": FEATURE_COLUMNS,
            "classes": sorted(int(c) for c in np.unique(y_train)),
        }, f, indent=2)

    print(f"Saved model, scaler, and feature list to {MODEL_DIR}/")
    print("Run evaluate.py for full test-set metrics (precision/recall/F1/confusion matrix/ROC-AUC).")


if __name__ == "__main__":
    main()
