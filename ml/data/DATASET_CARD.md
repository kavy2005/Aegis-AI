# synthetic_patients.csv — Dataset Card

**This is SYNTHETIC data. It is not real patient data and must never be presented as such.**

## Generation
Produced by `generate_synthetic_data.py` (fixed random seed = 42, fully reproducible).
3,000 rows. Each row is a randomly generated "patient" whose lab/vital values are sampled
from distributions centered on the same default reference ranges used by
`backend/app/risk_engine/reference_ranges.py`, with a randomly assigned severity tier
controlling how many parameters (and how far) are pushed outside the normal range.

## Labeling
The `target` column (risk level 1-5) is produced by running each synthetic patient's
values through the actual backend risk engine (`interpret_value` + `compute_risk`) —
the same deterministic, rule-based logic the live API uses — then randomly flipping
~10% of labels by one level to simulate real-world labeling noise. This keeps the ML
task consistent with the rest of the app rather than inventing a separate, contradictory
notion of "risk."

## Columns
| Column | Description |
|---|---|
| patient_id | Synthetic sequential ID |
| age | 18-85, uniform |
| sex | "male" / "female" |
| hemoglobin, fasting_glucose, hba1c, ldl, hdl, triglycerides, creatinine, alt, ast, systolic_bp, diastolic_bp, heart_rate, spo2, bmi | Synthetic lab/vital values |
| target | AEGIS Risk Support Level, 1 (healthy) to 5 (emergency) |

## License
CC0 / public domain — generated data, no real-world source, free to use and modify.

## Known limitations
- Parameters are sampled independently (aside from the tier-level correlation); real
  clinical values correlate with each other (e.g., BMI with blood pressure) in ways this
  generator does not model.
- Label noise is uniform random, not representative of any specific real-world
  disagreement pattern between clinicians.
- Intended purpose: demonstrating a working, evaluable training pipeline — not for
  drawing any real medical conclusions.
