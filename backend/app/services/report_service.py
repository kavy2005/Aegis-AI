from typing import List, Dict, Optional

from app.ocr.extraction import extract_text
from app.ocr.parser import parse_report_text
from app.risk_engine.parameter_dictionary import normalize_label
from app.risk_engine.reference_ranges import interpret_value
from app.risk_engine.scoring import compute_risk
from app.risk_engine.explanation import build_explanation
from app.ai.explain import get_explanation


def extract_and_normalize(file_bytes: bytes, filename: str) -> Dict:
    """Upload step: OCR/extract, parse into rows, normalize labels. No scoring yet --
    the user gets a chance to review/correct before analysis runs."""
    extraction = extract_text(file_bytes, filename)
    rows = parse_report_text(extraction["text"])
    for row in rows:
        row["canonical_parameter"] = normalize_label(row["raw_label"])
    return {"raw_text": extraction["text"], "extraction_method": extraction["method"], "rows": rows}


def analyze_findings(
    rows: List[Dict],
    sex: Optional[str] = None,
    language: str = "en",
) -> Dict:
    """Analysis step: interpret each row against reference ranges, score, explain."""
    findings = []
    for row in rows:
        canonical = row.get("canonical_parameter")
        value = row.get("value")
        if value is None:
            continue
        interpretation = interpret_value(
            canonical,
            value,
            report_low=row.get("reference_low"),
            report_high=row.get("reference_high"),
            sex=sex,
        )
        findings.append({
            "raw_label": row.get("raw_label"),
            "canonical_parameter": canonical,
            "value": value,
            "unit": row.get("unit"),
            **interpretation,
        })

    risk = compute_risk(findings)
    rule_based = build_explanation(findings, risk, language=language)

    structured_input = {
        "findings": [
            {
                "parameter": f.get("canonical_parameter") or f.get("raw_label"),
                "value": f.get("value"),
                "unit": f.get("unit"),
                "flag": f.get("flag"),
                "severity": f.get("severity"),
            }
            for f in findings if f.get("flag") in ("high", "low")
        ],
        "risk_level": risk["level"],
        "score": risk["score"],
    }
    explanation = get_explanation(structured_input, rule_based)

    return {"findings": findings, "risk": risk, "explanation": explanation}
