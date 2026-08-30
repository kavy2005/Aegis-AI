"""
Explanation engine.

Converts structured findings (already decided by the risk engine) into
plain-language text. This module never decides whether something is
abnormal -- it only explains what reference_ranges/scoring already found,
so the "source of truth" stays in one place as the spec requires.
"""
from typing import List, Dict, Optional

PARAMETER_BLURBS = {
    "hemoglobin": "Hemoglobin carries oxygen in your blood. A value outside range can relate to anemia, nutrition, hydration, or blood loss.",
    "rbc": "Red blood cells carry oxygen through the body. Values outside range can relate to anemia or other blood conditions.",
    "wbc": "White blood cells are part of your immune system. Values outside range can relate to infection, inflammation, or other causes.",
    "platelets": "Platelets help your blood clot. Values outside range can affect bleeding or clotting risk.",
    "hematocrit": "Hematocrit is the proportion of blood made up of red cells, and moves together with hemoglobin.",
    "mcv": "MCV describes the average size of your red blood cells, useful for narrowing down the type of anemia.",
    "mch": "MCH describes the average amount of hemoglobin per red blood cell -- a distinct index from total hemoglobin.",
    "mchc": "MCHC describes the hemoglobin concentration within your red blood cells.",
    "neutrophils": "Neutrophils are a type of white blood cell that responds first to infection; values outside range can relate to infection or inflammation.",
    "lymphocytes": "Lymphocytes are white blood cells central to your immune response; values outside range can relate to infection or other conditions.",
    "mid_cells": "MID (or 'mixed cell') count groups monocytes, eosinophils, and basophils together; this reading is analyzer-specific.",
    "plcr": "P-LCR reflects the proportion of larger platelets in the blood, which can relate to platelet turnover.",
    "mpv": "MPV is the average size of your platelets; can relate to how actively new platelets are being produced.",
    "pdw": "PDW reflects how much platelet sizes vary; used alongside other platelet indices.",
    "pct": "Plateletcrit reflects the total volume platelets occupy in the blood.",
    "rdw": "RDW reflects how much red blood cell sizes vary, useful alongside MCV for classifying anemia.",
    "rdw_sd": "RDW-SD is another way of measuring how much red blood cell sizes vary.",
    "fasting_glucose": "Fasting glucose reflects blood sugar control. Elevated values can relate to prediabetes or diabetes.",
    "random_glucose": "Random glucose is a blood sugar snapshot and is more variable than a fasting value.",
    "hba1c": "HbA1c reflects average blood sugar over the past ~3 months and is used to screen for diabetes.",
    "total_cholesterol": "Total cholesterol is a general marker of cardiovascular risk.",
    "ldl": "LDL is often called 'bad' cholesterol; higher levels are linked to cardiovascular risk over time.",
    "hdl": "HDL is often called 'good' cholesterol; lower levels are linked to higher cardiovascular risk.",
    "triglycerides": "Triglycerides are a type of blood fat; elevated levels relate to diet, weight, and cardiovascular risk.",
    "creatinine": "Creatinine is a waste product filtered by the kidneys; elevated levels can indicate reduced kidney function.",
    "bun": "BUN reflects kidney and hydration status.",
    "urea": "Urea is a waste product cleared by the kidneys.",
    "uric_acid": "Uric acid is a waste product from normal cell breakdown; elevated levels relate to gout risk and kidney function.",
    "egfr": "eGFR estimates how well your kidneys are filtering blood.",
    "alt": "ALT is a liver enzyme; elevated levels can indicate liver stress or damage.",
    "ast": "AST is a liver (and muscle) enzyme; elevated levels can indicate liver stress or damage.",
    "alp": "ALP relates to liver and bone activity.",
    "bilirubin": "Bilirubin relates to how your liver processes red blood cell breakdown.",
    "albumin": "Albumin reflects liver function and nutritional status.",
    "sodium": "Sodium is an electrolyte that affects fluid balance and nerve/muscle function.",
    "potassium": "Potassium is an electrolyte important for heart and muscle function; both high and low values can be significant.",
    "calcium": "Calcium supports bone, nerve, and muscle function.",
    "systolic_bp": "Systolic blood pressure is the pressure in your arteries when your heart beats.",
    "diastolic_bp": "Diastolic blood pressure is the pressure in your arteries between heartbeats.",
    "heart_rate": "Heart rate outside the typical resting range can relate to many causes, from fitness level to underlying conditions.",
    "spo2": "SpO2 measures blood oxygen saturation; low values can indicate a breathing or circulation problem.",
    "temperature": "Body temperature outside the typical range can indicate infection or other illness.",
    "respiratory_rate": "Respiratory rate outside the typical range can indicate a breathing or metabolic issue.",
    "bmi": "BMI is a general screening measure relating weight to height, not a full picture of health.",
    "vldl": "VLDL carries triglycerides in the blood and is usually calculated from your triglyceride level; elevated levels relate to cardiovascular risk.",
    "lipase": "Lipase is an enzyme from the pancreas; elevated levels can indicate pancreatic inflammation or other pancreatic issues.",
    "amylase": "Amylase is another pancreatic (and salivary) enzyme; elevated levels can relate to pancreatic inflammation.",
    "vitamin_d": "Vitamin D supports bone and immune health; low levels are common and usually addressed through diet, sun exposure, or supplements.",
    "vitamin_b12": "Vitamin B12 supports nerve function and red blood cell production; low levels can relate to diet or absorption issues.",
    "tsh": "TSH regulates thyroid hormone production; high or low levels can indicate an underactive or overactive thyroid.",
    "t3": "T3 is a thyroid hormone; abnormal levels relate to thyroid over- or under-activity.",
    "t4": "T4 is the main hormone produced by the thyroid; abnormal levels relate to thyroid over- or under-activity.",
    "crp": "CRP is a marker of inflammation in the body; elevated levels can relate to infection, injury, or chronic inflammatory conditions.",
    "ra_factor": "Rheumatoid factor is an antibody sometimes associated with rheumatoid arthritis and other autoimmune conditions, though it can also be elevated for unrelated reasons.",
}

_NEXT_STEPS_BY_LEVEL = {
    1: ["No abnormal findings detected in this report.", "Continue routine checkups as usual."],
    2: ["Keep an eye on the flagged values.", "Mention them at your next routine checkup."],
    3: ["Consult a qualified healthcare professional to review these findings.", "Bring this report and any symptoms you're experiencing to that visit."],
    4: ["Prompt medical attention is recommended.", "Contact a doctor or clinic soon rather than waiting for a routine visit."],
    5: ["Seek immediate professional or emergency medical assistance.", "Do not wait -- contact emergency services or go to the nearest facility."],
}

_HI_STRINGS = {
    "summary_template": "aapki report mein {n} parameter di gayi reference range se bahar hain.",
    "no_abnormal": "aapki report mein koi abnormal parameter nahi paya gaya.",
    "next_steps_1": ["is report mein koi abnormal finding nahi hai.", "apni routine checkups jaari rakhein."],
    "next_steps_2": ["flag kiye gaye values par nazar rakhein.", "agli routine checkup mein inka zikr karein."],
    "next_steps_3": ["in findings ko dekhne ke liye kisi qualified doctor se salaah lein.", "apne symptoms ke saath yeh report bhi saath le jaayein."],
    "next_steps_4": ["turant medical attention lene ki salaah di jaati hai.", "routine visit ka wait kiye bina jald doctor ya clinic se sampark karein."],
    "next_steps_5": ["turant professional ya emergency medical sahayata lein.", "wait na karein -- emergency services se sampark karein ya nazdeeki facility jaayein."],
    "urgent_warning": "high-risk findings paayi gayi hain. kripya turant professional medical attention lein.",
}


def build_explanation(
    findings: List[Dict],
    risk: Dict,
    language: str = "en",
) -> Dict:
    abnormal = [f for f in findings if f.get("flag") in ("high", "low") and f.get("severity", 0) > 0]

    if language == "hi":
        summary = (
            _HI_STRINGS["summary_template"].format(n=len(abnormal))
            if abnormal else _HI_STRINGS["no_abnormal"]
        )
        next_steps = _HI_STRINGS.get(f"next_steps_{risk['level']}", [])
        urgent_warning = _HI_STRINGS["urgent_warning"] if risk["level"] >= 4 else None
    else:
        summary = (
            f"Your report contains {len(abnormal)} parameter(s) outside the reference range."
            if abnormal else "No parameters outside the reference range were detected."
        )
        next_steps = _NEXT_STEPS_BY_LEVEL.get(risk["level"], [])
        urgent_warning = (
            "High-risk findings were detected. Please seek professional medical attention promptly."
            if risk["level"] >= 4 else None
        )

    explanation_items = []
    for f in abnormal:
        canonical = f.get("canonical_parameter")
        blurb = PARAMETER_BLURBS.get(canonical, "This value fell outside the reference range used for this report.")
        explanation_items.append({
            "parameter": canonical or f.get("raw_label"),
            "value": f.get("value"),
            "unit": f.get("unit"),
            "flag": f.get("flag"),
            "why_it_matters": blurb,
        })

    return {
        "summary": summary,
        "abnormal_findings": [f.get("canonical_parameter") or f.get("raw_label") for f in abnormal],
        "risk_level": risk["level"],
        "explanation": explanation_items,
        "recommended_next_steps": next_steps,
        "urgent_warning": urgent_warning,
    }
