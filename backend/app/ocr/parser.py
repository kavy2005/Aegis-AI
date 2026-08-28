"""
Turns raw extracted text into a list of {label, value, unit, ref_low, ref_high}
rows. Handles the common lab-report line shapes:

    Hemoglobin: 10.2 g/dL (12.0-15.5)
    LDL Cholesterol - 156 mg/dL
    Glucose (Fasting)   168   mg/dL   Ref: 70-100
    Haemoglobin 12.2 g/dL 13-17          <- OCR output, no separator, bare-hyphen range
    Serum Triglycerides 217.27 mg/dL 30 - 200
    Blood Pressure: 118/76 mmHg

Matching strategy: find the first STANDALONE number in the line and treat
everything before it as the label. This deliberately avoids hunting for a
label/value separator character (":" or "-") -- a bare hyphen is ambiguous
between "Label - value" and a "13-17" reference range with no parentheses,
which is the single most common real-world lab-report format and OCR's
default rendering of one. Anchoring on the first number sidesteps that
ambiguity entirely. A negative lookbehind keeps digits embedded in a label
itself (HbA1c, B12) from being mistaken for the value.

This is a prototype-grade parser tuned for common report formats, not a
general-purpose lab-report OCR parser -- real-world reports vary enormously
in layout, which is why the UI always shows the user what was detected and
lets them correct it before analysis (see /reports/{id}/analyze).
"""
import re
from typing import List, Dict, Optional

# A "standalone" number: not immediately preceded by a letter or digit, so
# the "1" in "HbA1c" or the "12" in "B12" never matches as a value.
_FIRST_NUMBER_RE = re.compile(r"(?<![A-Za-z0-9])-?\d+(?:\.\d+)?")
_UNIT_RE = re.compile(r"^\s*[:\-]?\s*([A-Za-z\u00b5%][A-Za-z0-9/%\u00b5.]*)")
_RANGE_RE = re.compile(r"(-?\d+(?:\.\d+)?)\s*(?:-|to|\u2013)\s*(-?\d+(?:\.\d+)?)")
_BP_RE = re.compile(
    r"^(?P<label>[A-Za-z\s]*blood\s*pressure[A-Za-z\s]*|bp)\s*[:\-]?\s*"
    r"(?P<sys>\d+)\s*/\s*(?P<dia>\d+)",
    re.IGNORECASE,
)
_LABEL_STRIP_CHARS = " \t:.-"


def _parse_line(line: str) -> Optional[Dict]:
    num_match = _FIRST_NUMBER_RE.search(line)
    if not num_match:
        return None

    label = line[:num_match.start()].strip(_LABEL_STRIP_CHARS)
    if not label or not re.search(r"[A-Za-z]", label):
        return None

    value = float(num_match.group())
    remainder = line[num_match.end():]

    unit_match = _UNIT_RE.match(remainder)
    unit = unit_match.group(1).strip() if unit_match else None

    ref_low = ref_high = None
    range_match = _RANGE_RE.search(remainder)
    if range_match:
        ref_low = float(range_match.group(1))
        ref_high = float(range_match.group(2))

    return {"raw_label": label, "value": value, "unit": unit,
            "reference_low": ref_low, "reference_high": ref_high}


def parse_report_text(text: str) -> List[Dict]:
    rows: List[Dict] = []
    if not text:
        return rows

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        bp_match = _BP_RE.match(line)
        if bp_match:
            rows.append({"raw_label": "Systolic BP", "value": float(bp_match.group("sys")), "unit": "mmHg",
                         "reference_low": None, "reference_high": None})
            rows.append({"raw_label": "Diastolic BP", "value": float(bp_match.group("dia")), "unit": "mmHg",
                         "reference_low": None, "reference_high": None})
            continue

        row = _parse_line(line)
        if row:
            rows.append(row)

    return rows
