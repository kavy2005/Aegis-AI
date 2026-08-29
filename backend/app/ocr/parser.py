"""
Turns raw extracted text into a list of {label, value, unit, ref_low, ref_high}
rows. Handles the common lab-report line shapes:

    Hemoglobin: 10.2 g/dL (12.0-15.5)
    LDL Cholesterol - 156 mg/dL
    Glucose (Fasting)   168   mg/dL   Ref: 70-100
    Haemoglobin 12.2 g/dL 13-17          <- OCR output, no separator, bare-hyphen range
    Serum Triglycerides 217.27 mg/dL 30 - 200
    Vitamin D (25-OH)  40.7 ng/mL  30 - 100  <- parenthetical is part of the NAME
    Blood Pressure: 118/76 mmHg

Matching strategy: find the first STANDALONE number in the line, skipping any
number inside parentheses, and treat everything before it as the label. This
deliberately avoids hunting for a label/value separator character (":" or
"-") -- a bare hyphen is ambiguous between "Label - value" and a "13-17"
reference range with no parentheses, which is the single most common
real-world lab-report format and OCR's default rendering of one. Anchoring
on the first number sidesteps that ambiguity entirely. A negative lookbehind
keeps digits embedded in a label itself (HbA1c, B12) from being mistaken for
the value, and skipping parenthesized numbers keeps a compound test name
like "Vitamin D (25-OH)" from having its "25" mistaken for the result.

A real lab report page is mostly NOT lab values: accreditation numbers,
patient demographics, collection/print timestamps, page counters, specimen
IDs. Those all contain standalone numbers too ("Page 1 of 3", "AGE 48",
"PRINTED 22 Aug"), so number-detection alone over-matches badly. The second
filter -- _looks_like_lab_row() -- keeps a candidate only when it has a
recognized measurement unit and/or a reference-range pattern immediately
after the value, which is a STRUCTURAL property of lab rows, not a specific
test name, so it generalizes to reports with completely different tests.
This is why it's a unit *vocabulary* check (a bounded, well-known domain of
how results are united) rather than a label allowlist (an open-ended list of
what tests exist) -- adding a new test to a future report needs no change
here, the same way a real reader recognizes "217.27 mg/dL" as a lab result
without knowing what "Triglycerides" means.

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

# Known laboratory measurement units, broadest-common set, tolerant of
# common OCR letter/digit confusions (1/l/I). A bounded domain vocabulary of
# how results are UNITED, not a list of test names.
_KNOWN_UNITS = [
    r"m?c?g/d[l1]", r"m?g/l", r"n?g/m[l1]", r"pg/m[l1]",
    r"[mnpu\u03bc]?i[u1]\s?/\s?[ml][l1]?", r"u/[lm][l1]?",
    r"m?e?q/l", r"m?m?osm/kg", r"n?m?p?mol/l",
    r"million/[cu\u03bc][lm]?[l1]?", r"thousand/[cu\u03bc][lm]?[l1]?",
    r"cells?/[cu\u03bc]{1,2}[lm]{1,2}", r"/[cu\u03bc]{1,2}[lm]{1,2}",
    r"f[l1]", r"pg", r"mm/hr", r"mm\s?hg", r"bpm", r"breaths?/min", r"/min",
    r"kg/m\^?2", r"m[l1]/min(?:/1\.73\s?m2)?",
    r"sec(?:onds?)?", r"%",
]
_UNIT_ALTERNATION = "|".join(_KNOWN_UNITS)
_UNIT_AFTER_VALUE_RE = re.compile(rf"^\s*[:\-]?\s*({_UNIT_ALTERNATION})(?![A-Za-z])", re.IGNORECASE)

_UNIT_RE = re.compile(r"^\s*[:\-]?\s*([A-Za-z\u00b5%][A-Za-z0-9/%\u00b5.]*)")
_RANGE_RE = re.compile(r"(-?\d+(?:\.\d+)?)\s*(?:-|to|\u2013)\s*(-?\d+(?:\.\d+)?)")
_BP_RE = re.compile(
    r"^(?P<label>[A-Za-z\s]*blood\s*pressure[A-Za-z\s]*|bp)\s*[:\-]?\s*"
    r"(?P<sys>\d+)\s*/\s*(?P<dia>\d+)",
    re.IGNORECASE,
)
_LABEL_STRIP_CHARS = " \t:.-"


def _paren_spans(line: str):
    """[start, end) character ranges covered by (...) groups in the line."""
    spans = []
    depth = 0
    start = None
    for i, ch in enumerate(line):
        if ch == "(":
            if depth == 0:
                start = i
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
            if depth == 0 and start is not None:
                spans.append((start, i + 1))
                start = None
    return spans


def _first_number_outside_parens(line: str):
    """The first standalone number NOT inside a (...) group. A number in
    parentheses right after a label is almost always part of the test name
    itself (Vitamin D (25-OH), Glucose (Fasting)), never the result."""
    spans = _paren_spans(line)
    for m in _FIRST_NUMBER_RE.finditer(line):
        if not any(s <= m.start() < e for s, e in spans):
            return m
    return None


def _looks_like_lab_row(remainder: str) -> bool:
    if _UNIT_AFTER_VALUE_RE.match(remainder):
        return True
    if _RANGE_RE.search(remainder):
        return True
    return False


def _parse_line(line: str) -> Optional[Dict]:
    num_match = _first_number_outside_parens(line)
    if not num_match:
        return None

    label = line[:num_match.start()].strip(_LABEL_STRIP_CHARS)
    if not label or not re.search(r"[A-Za-z]", label):
        return None

    value = float(num_match.group())
    remainder = line[num_match.end():]

    if not _looks_like_lab_row(remainder):
        return None

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
