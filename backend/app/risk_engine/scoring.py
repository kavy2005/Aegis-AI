"""
The AEGIS Risk Support Score.

Deliberately simple and inspectable: every number that goes into the score
is visible on the finding itself, and the score -> level bands live in
thresholds_config.json, not buried in code. This is a support/triage
signal, not a diagnosis, and is explicitly documented as unvalidated.
"""
import json
import os
from typing import List, Dict

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "thresholds_config.json")
with open(_CONFIG_PATH) as f:
    _CONFIG = json.load(f)

BANDS = _CONFIG["bands"]
WEIGHTS = _CONFIG["weights"]


def score_to_level(score: int):
    for band in BANDS:
        if band["min"] <= score <= band["max"]:
            return band["level"], band["label"]
    return BANDS[-1]["level"], BANDS[-1]["label"]


def compute_risk(findings: List[Dict]) -> Dict:
    """
    findings: list of dicts, each with at least "flag" ("normal"/"high"/"low"/
    "unrecognized") and "severity" (0-100), as produced by
    reference_ranges.interpret_value(). Optionally "critical" (bool).
    """
    abnormal = [f for f in findings if f.get("flag") in ("high", "low") and f.get("severity", 0) > 0]
    critical_breach = any(f.get("critical") for f in findings)

    if not abnormal:
        score = 0
    else:
        severities = [f["severity"] for f in abnormal]
        max_severity = max(severities)
        avg_severity = sum(severities) / len(severities)
        count_factor = min(WEIGHTS["count_factor_cap"], WEIGHTS["count_factor_per_finding"] * len(abnormal))
        score = round(
            WEIGHTS["max_severity"] * max_severity
            + WEIGHTS["avg_severity"] * avg_severity
            + count_factor
        )
        score = max(0, min(100, score))

    if critical_breach:
        score = max(score, 90)

    level, label = score_to_level(score)
    if critical_breach:
        level, label = 5, BANDS[-1]["label"]

    return {
        "score": score,
        "level": level,
        "label": label,
        "abnormal_count": len(abnormal),
        "critical_breach": critical_breach,
    }
