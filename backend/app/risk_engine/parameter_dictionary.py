"""
Canonical medical parameter dictionary.

Different labs report the same test under different names ("Haemoglobin",
"Hb", "HGB"). This module maps any raw label text to one internal
canonical key so the rest of the pipeline only ever has to deal with one
name per test. This is intentionally data, not code -- new parameters or
aliases can be added here without touching the risk engine or the API.
"""
from typing import Optional
import re

PARAMETER_DICTIONARY = {
    "hemoglobin": {
        "aliases": ["hemoglobin", "haemoglobin", "hb", "hgb"],
        "unit": "g/dL", "category": "CBC",
    },
    "rbc": {
        "aliases": ["rbc", "rbc count", "red blood cell count", "red blood cells", "erythrocyte count"],
        "unit": "million/uL", "category": "CBC",
    },
    "wbc": {
        "aliases": ["wbc", "wbc count", "white blood cell count", "white blood cells", "tlc", "total leucocyte count"],
        "unit": "thousand/uL", "category": "CBC",
    },
    "platelets": {
        "aliases": ["platelets", "platelet count", "plt"],
        "unit": "thousand/uL", "category": "CBC",
    },
    "hematocrit": {
        "aliases": ["hematocrit", "haematocrit", "hct", "pcv", "packed cell volume"],
        "unit": "%", "category": "CBC",
    },
    "mcv": {
        "aliases": ["mcv", "mean corpuscular volume", "mean cell volume", "mcv (mean cell volume)"],
        "unit": "fL", "category": "CBC",
    },
    "mch": {
        "aliases": ["mch", "mean corpuscular hemoglobin", "mean corpus. haemoglobin",
                    "mch (mean corpus. haemoglobin)"],
        "unit": "pg", "category": "CBC",
    },
    "mchc": {
        "aliases": ["mchc", "mean corpuscular hemoglobin concentration", "mean corpus. hb conc.",
                    "mchc (mean corpus. hb conc.)"],
        "unit": "g/dL", "category": "CBC",
    },
    "neutrophils": {
        "aliases": ["neutrophils", "neutrophil count", "neutrophils %", "neut", "polys"],
        "unit": "%", "category": "CBC",
    },
    "lymphocytes": {
        "aliases": ["lymphocytes", "lymphocyte count", "lymphocytes %", "lymph"],
        "unit": "%", "category": "CBC",
    },
    "mid_cells": {
        "aliases": ["mid", "mid cells", "mid%", "mid %"],
        "unit": "%", "category": "CBC",
    },
    "plcr": {
        "aliases": ["lpcr", "p-lcr", "plcr", "platelet large cell ratio"],
        "unit": "%", "category": "CBC",
    },
    "mpv": {
        "aliases": ["mpv", "mean platelet volume"],
        "unit": "fL", "category": "CBC",
    },
    "pdw": {
        "aliases": ["pdw", "platelet distribution width"],
        "unit": "%", "category": "CBC",
    },
    "pct": {
        "aliases": ["pct", "plateletcrit"],
        "unit": "%", "category": "CBC",
    },
    "rdw": {
        "aliases": ["rdw", "rdw-cv", "rdw cv", "red cell distribution width"],
        "unit": "%", "category": "CBC",
    },
    "rdw_sd": {
        # "RDWA" is treated as an OCR/formatting variant of RDW-SD (the
        # hyphen dropped and "SD" run together) seen in the real report --
        # a judgment call, not a standard abbreviation; verify against the
        # source report if a lab genuinely uses "RDWA" to mean something else.
        "aliases": ["rdw-sd", "rdw sd", "rdwsd", "rdwa"],
        "unit": "fL", "category": "CBC",
    },
    "fasting_glucose": {
        "aliases": ["fasting glucose", "fasting blood glucose", "fbs", "fpg", "fasting blood sugar"],
        "unit": "mg/dL", "category": "Glucose",
    },
    "random_glucose": {
        "aliases": ["random glucose", "random blood sugar", "rbs", "post prandial glucose", "ppbs"],
        "unit": "mg/dL", "category": "Glucose",
    },
    "hba1c": {
        "aliases": ["hba1c", "hb a1c", "hbalc", "glycated hemoglobin", "glycosylated hemoglobin", "a1c"],
        "unit": "%", "category": "Glucose",
    },
    "total_cholesterol": {
        "aliases": ["total cholesterol", "cholesterol total", "cholesterol"],
        "unit": "mg/dL", "category": "Lipid",
    },
    "ldl": {
        "aliases": ["ldl", "ldl cholesterol", "ldl-c", "low density lipoprotein"],
        "unit": "mg/dL", "category": "Lipid",
    },
    "hdl": {
        "aliases": ["hdl", "hdl cholesterol", "hdl-c", "high density lipoprotein"],
        "unit": "mg/dL", "category": "Lipid",
    },
    "triglycerides": {
        "aliases": ["triglycerides", "tg", "trigs"],
        "unit": "mg/dL", "category": "Lipid",
    },
    "vldl": {
        "aliases": ["vldl", "vldl cholesterol", "vldl-c"],
        "unit": "mg/dL", "category": "Lipid",
    },
    "creatinine": {
        "aliases": ["creatinine", "serum creatinine", "s. creatinine", "creat"],
        "unit": "mg/dL", "category": "Kidney",
    },
    "bun": {
        "aliases": ["bun", "blood urea nitrogen"],
        "unit": "mg/dL", "category": "Kidney",
    },
    "urea": {
        "aliases": ["urea", "blood urea", "serum urea"],
        "unit": "mg/dL", "category": "Kidney",
    },
    "uric_acid": {
        "aliases": ["uric acid", "serum uric acid", "ua"],
        "unit": "mg/dL", "category": "Kidney",
    },
    "egfr": {
        "aliases": ["egfr", "gfr", "estimated glomerular filtration rate"],
        "unit": "mL/min/1.73m2", "category": "Kidney",
    },
    "alt": {
        "aliases": ["alt", "sgpt", "alanine aminotransferase"],
        "unit": "U/L", "category": "Liver",
    },
    "ast": {
        "aliases": ["ast", "sgot", "aspartate aminotransferase"],
        "unit": "U/L", "category": "Liver",
    },
    "alp": {
        "aliases": ["alp", "alkaline phosphatase"],
        "unit": "U/L", "category": "Liver",
    },
    "bilirubin": {
        "aliases": ["bilirubin", "total bilirubin", "bilirubin total"],
        "unit": "mg/dL", "category": "Liver",
    },
    "albumin": {
        "aliases": ["albumin", "serum albumin"],
        "unit": "g/dL", "category": "Liver",
    },
    "sodium": {
        "aliases": ["sodium", "na", "na+", "serum sodium"],
        "unit": "mEq/L", "category": "Electrolytes",
    },
    "potassium": {
        "aliases": ["potassium", "k", "k+", "serum potassium"],
        "unit": "mEq/L", "category": "Electrolytes",
    },
    "calcium": {
        "aliases": ["calcium", "ca", "serum calcium"],
        "unit": "mg/dL", "category": "Electrolytes",
    },
    "systolic_bp": {
        "aliases": ["systolic bp", "systolic blood pressure", "sbp"],
        "unit": "mmHg", "category": "Vitals",
    },
    "diastolic_bp": {
        "aliases": ["diastolic bp", "diastolic blood pressure", "dbp"],
        "unit": "mmHg", "category": "Vitals",
    },
    "heart_rate": {
        "aliases": ["heart rate", "pulse", "pulse rate", "hr"],
        "unit": "bpm", "category": "Vitals",
    },
    "spo2": {
        "aliases": ["spo2", "oxygen saturation", "o2 saturation", "sao2"],
        "unit": "%", "category": "Vitals",
    },
    "temperature": {
        "aliases": ["temperature", "temp", "body temperature"],
        "unit": "F", "category": "Vitals",
    },
    "respiratory_rate": {
        "aliases": ["respiratory rate", "resp rate", "rr", "breathing rate"],
        "unit": "breaths/min", "category": "Vitals",
    },
    "bmi": {
        "aliases": ["bmi", "body mass index"],
        "unit": "kg/m2", "category": "Vitals",
    },
    "lipase": {
        "aliases": ["lipase", "serum lipase"],
        "unit": "U/L", "category": "Pancreatic",
    },
    "amylase": {
        "aliases": ["amylase", "serum amylase"],
        "unit": "U/L", "category": "Pancreatic",
    },
    "vitamin_d": {
        "aliases": ["vitamin d", "vitamin d (25-oh)", "25-oh vitamin d", "25(oh)d", "vit d", "vit. d"],
        "unit": "ng/mL", "category": "Vitamins",
    },
    "vitamin_b12": {
        "aliases": ["vitamin b12", "serum vitamin b12", "vit b12", "vit. b12", "b12", "cobalamin"],
        "unit": "pg/mL", "category": "Vitamins",
    },
    "tsh": {
        "aliases": ["tsh", "thyroid stimulating hormone", "s. tsh", "serum tsh"],
        "unit": "mIU/L", "category": "Thyroid",
    },
    "t3": {
        "aliases": ["t3", "serum t3", "triiodothyronine", "total t3"],
        "unit": "ng/dL", "category": "Thyroid",
    },
    "t4": {
        "aliases": ["t4", "serum t4", "thyroxine", "total t4"],
        "unit": "\u00b5g/dL", "category": "Thyroid",
    },
    "crp": {
        "aliases": ["crp", "c-reactive protein", "c reactive protein", "hs-crp", "hscrp"],
        "unit": "mg/L", "category": "Inflammation",
    },
    "ra_factor": {
        "aliases": ["ra factor", "rheumatoid factor", "rf", "ra"],
        "unit": "IU/mL", "category": "Autoimmune",
    },
}

# Reverse index: normalized alias string -> canonical key, built once at import time.
_ALIAS_INDEX = {}
for canonical, meta in PARAMETER_DICTIONARY.items():
    for alias in meta["aliases"]:
        _ALIAS_INDEX[alias.strip().lower()] = canonical


def normalize_label(raw_label: str) -> Optional[str]:
    """Map a raw report label to a canonical parameter key, or None if unrecognized."""
    if not raw_label:
        return None
    cleaned = raw_label.strip().lower()
    cleaned = cleaned.rstrip(":").strip()

    if cleaned in _ALIAS_INDEX:
        return _ALIAS_INDEX[cleaned]

    # Contextual disambiguation for glucose-family labels, which labs phrase
    # many different ways and which map to different canonical tests
    # depending on context words present.
    if "hba1c" in cleaned or "glycated" in cleaned or "glycosylated" in cleaned or cleaned == "a1c":
        return "hba1c"
    if "fasting" in cleaned and ("glucose" in cleaned or "sugar" in cleaned):
        return "fasting_glucose"
    if ("random" in cleaned or "post prandial" in cleaned or "pp" in cleaned) and (
        "glucose" in cleaned or "sugar" in cleaned
    ):
        return "random_glucose"
    if "glucose" in cleaned or "sugar" in cleaned:
        # No qualifier present -- default to fasting glucose as the most
        # commonly reported single glucose value. Documented limitation.
        return "fasting_glucose"

    # "MCH" (Mean Corpuscular Hemoglobin) is a distinct CBC index from plain
    # Hemoglobin -- but its parenthetical expansion as printed by many labs
    # ("Mean Corpus. Haemoglobin") literally contains the word "haemoglobin",
    # which is itself an alias of the "hemoglobin" canonical. Left to the
    # generic substring fallback below, "haemoglobin" would be found first
    # (its dictionary entry comes first) and MCH would be misclassified as
    # plain Hemoglobin. Checked here as a whole word via \b so it can never
    # match inside "MCHC", which is a separate, unrelated canonical.
    if re.search(r"\bmch\b", cleaned):
        return "mch"
    if re.search(r"\bmchc\b", cleaned):
        return "mchc"

    # Fall back to a substring match against known aliases for minor OCR noise
    # (extra words, punctuation) that an exact match would miss. Restricted to
    # aliases of length >= 4: short symbols like "k" or "na" are exact-match
    # only, since as substrings they false-positive against unrelated text
    # (e.g. "k" inside "unknown").
    for alias, canonical in _ALIAS_INDEX.items():
        if len(alias) < 4:
            continue
        if alias in cleaned or cleaned in alias:
            return canonical

    return None


def get_parameter_meta(canonical: str) -> Optional[dict]:
    return PARAMETER_DICTIONARY.get(canonical)
