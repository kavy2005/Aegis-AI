"""
Scores the trained model against the held-out test set produced by train.py
(never re-splits the data, so this is always the same test set training
never saw). Reports accuracy, precision/recall/F1 (per-class and macro),
confusion matrix, and multiclass ROC-AUC (one-vs-rest).
"""
import json
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score, precision_recall_fscore_support,
    confusion_matrix, roc_auc_score, classification_report,
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")


def main():
    model = joblib.load(os.path.join(MODEL_DIR, "model.pkl"))
    scaler = joblib.load(os.path.join(MODEL_DIR, "scaler.pkl"))
    with open(os.path.join(MODEL_DIR, "feature_names.json")) as f:
        feature_names = json.load(f)

    test_df = pd.read_csv(os.path.join(DATA_DIR, "test.csv"))
    X_test = scaler.transform(test_df[feature_names].values)
    y_test = test_df["target"].values

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)

    accuracy = accuracy_score(y_test, y_pred)
    precision, recall, f1, support = precision_recall_fscore_support(
        y_test, y_pred, average="macro", zero_division=0
    )
    cm = confusion_matrix(y_test, y_pred, labels=sorted(model.classes_))

    try:
        roc_auc = roc_auc_score(y_test, y_proba, multi_class="ovr", average="macro")
    except ValueError as e:
        roc_auc = None
        print(f"ROC-AUC skipped: {e}")

    print(f"Test set size: {len(test_df)}")
    print(f"Accuracy:  {accuracy:.3f}")
    print(f"Precision (macro): {precision:.3f}")
    print(f"Recall (macro):    {recall:.3f}")
    print(f"F1 (macro):        {f1:.3f}")
    if roc_auc is not None:
        print(f"ROC-AUC (macro, OvR): {roc_auc:.3f}")
    print("\nPer-class report:")
    print(classification_report(y_test, y_pred, zero_division=0))
    print("Confusion matrix (rows=actual, cols=predicted), classes:", sorted(model.classes_))
    print(cm)

    report = {
        "test_size": len(test_df),
        "accuracy": round(float(accuracy), 4),
        "precision_macro": round(float(precision), 4),
        "recall_macro": round(float(recall), 4),
        "f1_macro": round(float(f1), 4),
        "roc_auc_macro_ovr": round(float(roc_auc), 4) if roc_auc is not None else None,
        "classes": [int(c) for c in sorted(model.classes_)],
        "confusion_matrix": cm.tolist(),
    }
    with open(os.path.join(MODEL_DIR, "evaluation_report.json"), "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nSaved evaluation_report.json to {MODEL_DIR}/")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(5, 4.5))
        im = ax.imshow(cm, cmap="Blues")
        classes = sorted(model.classes_)
        ax.set_xticks(range(len(classes)), labels=[f"L{c}" for c in classes])
        ax.set_yticks(range(len(classes)), labels=[f"L{c}" for c in classes])
        ax.set_xlabel("Predicted level")
        ax.set_ylabel("Actual level")
        ax.set_title("AEGIS AI baseline model -- confusion matrix")
        for i in range(len(classes)):
            for j in range(len(classes)):
                ax.text(j, i, cm[i, j], ha="center", va="center",
                        color="white" if cm[i, j] > cm.max() / 2 else "black")
        fig.colorbar(im)
        fig.tight_layout()
        fig.savefig(os.path.join(MODEL_DIR, "confusion_matrix.png"), dpi=150)
        print(f"Saved confusion_matrix.png to {MODEL_DIR}/")
    except ImportError:
        print("matplotlib not installed -- skipping confusion_matrix.png (metrics above are unaffected).")


if __name__ == "__main__":
    main()
