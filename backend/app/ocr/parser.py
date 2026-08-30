"""
Turns raw extracted text into a list of {label, value, unit, ref_low, ref_high}
rows. Handles two distinct real-world layouts:

ONE-LINE format (label, value, unit, range all on the same line):
    Hemoglobin: 10.2 g/dL (12.0-15.5)
    LDL Cholesterol - 156 mg/dL
    Glucose (Fasting)   168   mg/dL   Ref: 70-100
    Haemoglobin 12.2 g/dL 13-17          <- OCR output, no separator, bare-hyphen range
    Serum Triglycerides 217.27 mg/dL 30 - 200
    Vitamin D (25-OH)  40.7 ng/mL  30 - 100  <- parenthetical is part of the NAME
    Blood Pressure: 118/76 mmHg

MULTI-LINE format (each cell of the results table lands on its own line --
common when a PDF's text layer preserves a table's row-by-row/column-by-column
reading order instead of visual left-to-right order):
    Haemoglobin
    12.2
    g/dL
    13 - 17

    Serum Lipase
    41.5
    IU/l
    <38

Matching strategy for one-line rows: find the first STANDALONE number in the
line, skipping any number inside parentheses, and treat everything before it
as the label. This deliberately avoids hunting for a label/value separator
character (":" or "-") -- a bare hyphen is ambiguous between "Label - value"
and a "13-17" reference range with no parentheses, which is the single most
common real-world lab-report format and OCR's default rendering of one.
Anchoring on the first number sidesteps that ambiguity entirely. A negative
lookbehind keeps digits embedded in a label itself (HbA1c, B12) from being
mistaken for the value, and skipping parenthesized numbers keeps a compound
test name like "Vitamin D (25-OH)" from having its "25" mistaken for the
result.

Matching strategy for multi-line rows: a candidate label line is one with NO
standalone number of its own (the same "standalone number" test used above --
"HbA1c" and "VITAMIN D" qualify, a line with "48" in it doesn't). If the very
next line is ENTIRELY a bare number, and the following line(s) look like a
unit and/or a reference range, the group is read as one row and all of its
lines are consumed together. This is why label lines with embedded digits
(HbA1c) still work but lines carrying a real standalone number (a patient's
age, a page number) never get treated as the start of a row.

A real lab report page is mostly NOT lab values: accreditation numbers,
patient demographics, collection/print timestamps, page counters, specimen
IDs. Those all contain standalone numbers too ("Page 1 of 3", "AGE 48",
"PRINTED 22 Aug"), so number-detection alone over-matches badly. The second
filter -- _looks_like_lab_row() for one-line rows, and the unit/range check
in _parse_multiline_block() for multi-line rows -- keeps a candidate only
when it has a recognized measurement unit and/or a reference-range pattern,
which is a STRUCTURAL property of lab rows, not a specific test name, so it
generalizes to reports with completely different tests. This is why it's a
unit *vocabulary* check (a bounded, well-known domain of how results are
united) rather than a label allowlist (an open-ended list of what tests
exist) -- adding a new test to a future report needs no change here, the
same way a real reader recognizes "217.27 mg/dL" as a lab result without
knowing what "Triglycerides" means. Deliberately NOT a label blacklist
either: junk lines are rejected because they never have the number-then-unit
or number-then-range shape, not because their specific wording is
recognized -- a report with entirely different administrative text still
gets filtered correctly.

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

# A line that is NOTHING but a unit (the multi-line-table case), with an
# optional trailing period/colon that OCR/text-extraction sometimes leaves
# attached to the last cell of a row.
_UNIT_LINE_RE = re.compile(rf"^\s*({_UNIT_ALTERNATION})\s*[.:]?\s*$", re.IGNORECASE)

_UNIT_RE = re.compile(r"^\s*[:\-]?\s*([A-Za-z\u00b5%][A-Za-z0-9/%\u00b5.]*)")
_RANGE_RE = re.compile(r"(-?\d+(?:\.\d+)?)\s*(?:-|to|\u2013)\s*(-?\d+(?:\.\d+)?)")

# A reference range expressed as a one-sided comparator on its own line,
# e.g. "<38" (upper bound only) or ">10" (lower bound only) -- common for
# tests reported as "less than X is normal" rather than a two-sided range.
_COMPARATOR_LINE_RE = re.compile(r"^\s*(<=|>=|<|>|\u2264|\u2265)\s*(-?\d+(?:\.\d+)?)\s*$")

# A line that is nothing but a number -- the "value" cell of a multi-line
# table row, once the surrounding whitespace is stripped.
_BARE_NUMBER_LINE_RE = re.compile(r"^\s*-?\d+(?:\.\d+)?\s*$")

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


def _parse_multiline_block(lines: List[str], start: int):
    """Try to read a label/value/unit/range lab row spread across several
    consecutive lines -- the layout a PDF/OCR text layer commonly produces
    for a results table, where each cell becomes its own line instead of a
    single "label value unit range" line.

    Returns (row_dict, lines_consumed), or (None, 0) if `start` doesn't
    begin a recognizable multi-line row.
    """
    label_line = lines[start]
    if not label_line or not re.search(r"[A-Za-z]", label_line):
        return None, 0

    # A genuine multi-line label never carries a standalone number itself
    # (digits embedded in the name, like HbA1c, are fine -- they're not
    # "standalone"). A line WITH a standalone number is either a one-line
    # row -- handled by _parse_line -- or administrative text (an age, a
    # page number), never the start of a multi-line row.
    if _first_number_outside_parens(label_line) is not None:
        return None, 0

    if start + 1 >= len(lines):
        return None, 0
    value_line = lines[start + 1]
    if not _BARE_NUMBER_LINE_RE.match(value_line):
        return None, 0
    value = float(value_line)

    consumed = 2
    idx = start + 2
    unit = None

    if idx < len(lines) and _UNIT_LINE_RE.match(lines[idx]):
        unit = lines[idx].rstrip(" .:").strip()
        consumed += 1
        idx += 1

    ref_low = ref_high = None
    if idx < len(lines):
        range_line = lines[idx]
        range_match = _RANGE_RE.search(range_line)
        comparator_match = _COMPARATOR_LINE_RE.match(range_line)
        if range_match:
            ref_low = float(range_match.group(1))
            ref_high = float(range_match.group(2))
            consumed += 1
        elif comparator_match:
            symbol, bound = comparator_match.group(1), float(comparator_match.group(2))
            if symbol in ("<", "<=", "\u2264"):
                ref_high = bound
            else:
                ref_low = bound
            consumed += 1

    # Structural requirement, same as the one-line path: a bare number
    # following a text line is not enough on its own (that's just as true
    # of "AGE 48" as it is of "Haemoglobin 12.2") -- a unit or a reference
    # range must also be present for this to count as a genuine lab result.
    if unit is None and ref_low is None and ref_high is None:
        return None, 0

    label = label_line.strip(_LABEL_STRIP_CHARS)
    return {"raw_label": label, "value": value, "unit": unit,
            "reference_low": ref_low, "reference_high": ref_high}, consumed


def parse_report_text(text: str) -> List[Dict]:
    rows: List[Dict] = []
    if not text:
        return rows

    lines = [raw_line.strip() for raw_line in text.splitlines() if raw_line.strip()]

    i = 0
    while i < len(lines):
        line = lines[i]

        bp_match = _BP_RE.match(line)
        if bp_match:
            rows.append({"raw_label": "Systolic BP", "value": float(bp_match.group("sys")), "unit": "mmHg",
                         "reference_low": None, "reference_high": None})
            rows.append({"raw_label": "Diastolic BP", "value": float(bp_match.group("dia")), "unit": "mmHg",
                         "reference_low": None, "reference_high": None})
            i += 1
            continue

        block, consumed = _parse_multiline_block(lines, i)
        if block:
            rows.append(block)
            i += consumed
            continue

        row = _parse_line(line)
        if row:
            rows.append(row)
        i += 1

    return rows
