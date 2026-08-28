import os

from fastapi import APIRouter

from app.schemas.schemas import MLPredictRequest, MLPredictResponse

router = APIRouter(prefix="/ml", tags=["ml"])

_MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "ml", "models")
_MODEL_PATH = os.path.join(_MODEL_DIR, "model.pkl")
_SCALER_PATH = os.path.join(_MODEL_DIR, "scaler.pkl")
_FEATURES_PATH = os.path.join(_MODEL_DIR, "feature_names.json")

FEATURE_DEFAULTS = {
    "age": 40, "sex_male": 0, "hemoglobin": 14.0, "fasting_glucose": 90, "hba1c": 5.2,
    "ldl": 100, "hdl": 55, "triglycerides": 120, "creatinine": 0.9, "alt": 25, "ast": 25,
    "systolic_bp": 115, "diastolic_bp": 75, "heart_rate": 75, "spo2": 98, "bmi": 23,
}


def _load_model():
    if not (os.path.exists(_MODEL_PATH) and os.path.exists(_SCALER_PATH)):
        return None, None, None
    import joblib
    import json
    model = joblib.load(_MODEL_PATH)
    scaler = joblib.load(_SCALER_PATH)
    with open(_FEATURES_PATH) as f:
        feature_names = json.load(f)
    return model, scaler, feature_names


@router.post("/predict", response_model=MLPredictResponse)
def predict(payload: MLPredictRequest):
    model, scaler, feature_names = _load_model()
    if model is None:
        return MLPredictResponse(
            model_available=False,
            message="No trained model found yet. Run `python ml/train.py` to train the baseline model.",
        )

    row = payload.model_dump()
    sex = (row.pop("sex", "") or "").lower()
    row["sex_male"] = 1 if sex.startswith("m") else 0

    import numpy as np
    x = np.array([[row.get(name, FEATURE_DEFAULTS.get(name, 0)) or FEATURE_DEFAULTS.get(name, 0)
                    for name in feature_names]])
    x_scaled = scaler.transform(x)

    prediction = int(model.predict(x_scaled)[0])
    proba = model.predict_proba(x_scaled)[0]
    probabilities = {str(cls): round(float(p), 3) for cls, p in zip(model.classes_, proba)}

    contributors = []
    if hasattr(model, "coef_"):
        class_idx = list(model.classes_).index(prediction) if prediction in list(model.classes_) else 0
        coefs = model.coef_[class_idx] if model.coef_.ndim > 1 else model.coef_[0]
        contributions = x_scaled[0] * coefs
        ranked = sorted(zip(feature_names, contributions), key=lambda t: abs(t[1]), reverse=True)[:5]
        contributors = [{"feature": name, "contribution": round(float(val), 3)} for name, val in ranked]

    return MLPredictResponse(
        model_available=True,
        predicted_level=prediction,
        probabilities=probabilities,
        top_contributors=contributors,
    )
