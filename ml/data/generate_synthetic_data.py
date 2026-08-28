"""
Generates a SYNTHETIC patient dataset for training the demo ML model.

This is not real patient data -- see DATASET_CARD.md. Values are sampled
from distributions centered on the same reference ranges the backend risk
engine uses (backend/app/risk_engine/reference_ranges.py), then that exact
rule engine is reused to derive each patient's "true" risk level, so the
ML model is learning to approximate the same transparent scoring logic
from raw parameters -- with 10% label noise added so the task isn't
trivially perfect (real-world labels are never perfectly consistent either).
"""
import os
import sys
import csv
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
from app.risk_engine.reference_ranges import interpret_value  # noqa: E402
from app.risk_engine.scoring import compute_risk  # noqa: E402

random.seed(42)

OUT_PATH = os.path.join(os.path.dirname(__file__), "synthetic_patients.csv")
N_PATIENTS = 3000

# (healthy_mean, std, low_clip, high_clip, "high"|"low"|"either" = bad direction)
PARAM_PROFILE = {
    "hemoglobin": (13.8, 1.2, 6.0, 20.0, "low"),
    "fasting_glucose": (88, 8, 40, 500, "high"),
    "hba1c": (5.1, 0.3, 3.5, 14.0, "high"),
    "ldl": (95, 20, 30, 260, "high"),
    "hdl": (55, 12, 15, 100, "low"),
    "triglycerides": (100, 30, 30, 500, "high"),
    "creatinine": (0.9, 0.15, 0.3, 8.0, "high"),
    "alt": (25, 10, 5, 250, "high"),
    "ast": (25, 10, 5, 250, "high"),
    "systolic_bp": (113, 8, 75, 220, "either"),
    "diastolic_bp": (72, 6, 45, 140, "either"),
    "heart_rate": (75, 10, 35, 170, "either"),
    "spo2": (98, 1.2, 70, 100, "low"),
    "bmi": (22.5, 2.5, 14, 48, "either"),
}

TIERS = [
    ("healthy", 0.40, 0.04, 0.0),
    ("mild", 0.25, 0.18, 1.0),
    ("moderate", 0.20, 0.32, 1.8),
    ("high", 0.10, 0.45, 2.6),
    ("emergency", 0.05, 0.60, 3.6),
]
TIER_NAMES = [t[0] for t in TIERS]
TIER_WEIGHTS = [t[1] for t in TIERS]


def sample_value(param, affected, severity_mult):
    mean, std, lo_clip, hi_clip, direction = PARAM_PROFILE[param]
    value = random.gauss(mean, std)
    if affected:
        sign = 1 if direction == "high" else -1 if direction == "low" else random.choice([-1, 1])
        value += sign * severity_mult * std * random.uniform(1.2, 2.2)
    return round(max(lo_clip, min(hi_clip, value)), 2)


def force_critical(row, tier_severity):
    choice = random.choice(["spo2", "systolic_bp", "fasting_glucose"])
    if choice == "spo2":
        row["spo2"] = round(random.uniform(78, 89), 1)
    elif choice == "systolic_bp":
        row["systolic_bp"] = round(random.uniform(185, 210), 0)
    else:
        row["fasting_glucose"] = round(random.uniform(410, 480), 0)


def generate_patient(patient_id):
    tier_name, _, abnormal_prob, severity_mult = random.choices(TIERS, weights=TIER_WEIGHTS, k=1)[0]
    sex = random.choice(["male", "female"])
    age = random.randint(18, 85)

    row = {"patient_id": patient_id, "age": age, "sex": sex}
    for param in PARAM_PROFILE:
        affected = random.random() < abnormal_prob
        row[param] = sample_value(param, affected, severity_mult)

    if tier_name == "emergency" and random.random() < 0.7:
        force_critical(row, severity_mult)

    findings = []
    for param, value in row.items():
        if param in PARAM_PROFILE:
            findings.append({"canonical_parameter": param, **interpret_value(param, value, sex=sex)})
    risk = compute_risk(findings)

    target = risk["level"]
    if random.random() < 0.10:
        target = max(1, min(5, target + random.choice([-1, 1])))

    row["target"] = target
    return row


def main():
    fieldnames = ["patient_id", "age", "sex"] + list(PARAM_PROFILE.keys()) + ["target"]
    rows = [generate_patient(i) for i in range(1, N_PATIENTS + 1)]

    with open(OUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    counts = {}
    for r in rows:
        counts[r["target"]] = counts.get(r["target"], 0) + 1
    print(f"Wrote {len(rows)} synthetic patients to {OUT_PATH}")
    print("Target level distribution:", dict(sorted(counts.items())))


if __name__ == "__main__":
    main()
