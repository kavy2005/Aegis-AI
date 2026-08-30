import pytest

from app.ocr.parser import parse_report_text


def test_parses_label_value_unit_and_range():
    text = "Hemoglobin: 10.2 g/dL (12.0-15.5)"
    rows = parse_report_text(text)
    assert len(rows) == 1
    row = rows[0]
    assert row["raw_label"] == "Hemoglobin"
    assert row["value"] == 10.2
    assert row["unit"] == "g/dL"
    assert row["reference_low"] == 12.0
    assert row["reference_high"] == 15.5


def test_parses_multiple_lines():
    text = "\n".join([
        "Hemoglobin: 10.2 g/dL (12.0-15.5)",
        "LDL Cholesterol: 156 mg/dL (0-130)",
        "Fasting Glucose: 168 mg/dL (70-100)",
    ])
    rows = parse_report_text(text)
    assert len(rows) == 3
    assert rows[1]["raw_label"] == "LDL Cholesterol"
    assert rows[2]["value"] == 168


def test_parses_blood_pressure_into_two_rows():
    rows = parse_report_text("Blood Pressure: 118/76 mmHg")
    assert len(rows) == 2
    labels = {r["raw_label"] for r in rows}
    assert labels == {"Systolic BP", "Diastolic BP"}
    values = {r["raw_label"]: r["value"] for r in rows}
    assert values["Systolic BP"] == 118
    assert values["Diastolic BP"] == 76


def test_ignores_lines_without_a_value():
    text = "\n".join([
        "AEGIS AI - CBC Report",
        "Hemoglobin: 13.5 g/dL (12.0-17.0)",
        "-----",
    ])
    rows = parse_report_text(text)
    assert len(rows) == 1
    assert rows[0]["raw_label"] == "Hemoglobin"


def test_handles_missing_range():
    rows = parse_report_text("SpO2: 96 %")
    assert len(rows) == 1
    assert rows[0]["value"] == 96
    assert rows[0]["reference_low"] is None


def test_bare_hyphen_range_no_parentheses_no_separator():
    # Regression: OCR output commonly has no ':'/'-' between label and value,
    # and reference ranges are often bare "13-17" with no parentheses. The
    # label-matching used to "eat through" to that hyphen and misread the
    # range's upper bound as the value itself.
    rows = parse_report_text("Haemoglobin 12.2 g/dL 13-17")
    assert len(rows) == 1
    assert rows[0]["raw_label"] == "Haemoglobin"
    assert rows[0]["value"] == 12.2
    assert rows[0]["reference_low"] == 13.0
    assert rows[0]["reference_high"] == 17.0


def test_bare_hyphen_range_with_spaces():
    rows = parse_report_text("Serum Triglycerides 217.27 mg/dL 30 - 200")
    assert len(rows) == 1
    assert rows[0]["raw_label"] == "Serum Triglycerides"
    assert rows[0]["value"] == 217.27
    assert rows[0]["reference_high"] == 200.0


def test_label_with_embedded_digits_not_mistaken_for_value():
    rows = parse_report_text("HbA1c: 8.1 %")
    assert len(rows) == 1
    assert rows[0]["raw_label"] == "HbA1c"
    assert rows[0]["value"] == 8.1


# --- Header/footer/metadata rejection (real report had genuine lab rows
# alongside accreditation numbers, patient demographics, and timestamps;
# the parser used to extract the metadata numbers as if they were results) ---

@pytest.mark.parametrize("junk_line", [
    "AN ISO 9001:2015 CERTIFIED LABORATORY",
    "REG/REF: DWH 8515 PAGE 1 of 3",
    "Patient: Anjana AGE/GENDER 48 Yrs./Male",
    "COLL TIME 22 Aug 09:10",
    "PRN. TIME 22 Aug 11:40",
    "PLAIN 460473",
    "PRINTED 22 Aug 2026 Page 1 of 3",
    "UP TO 150 samples processed daily at this facility",
    "Page 2 of 3",
])
def test_rejects_header_footer_metadata_lines(junk_line):
    # None of these have a real measurement unit or a reference range, so
    # none should be mistaken for a lab result no matter what number is in them.
    assert parse_report_text(junk_line) == []


def test_parenthetical_in_label_not_mistaken_for_value():
    # The "25" in "(25-OH)" is part of the test name, not a result.
    rows = parse_report_text("Vitamin D (25-OH) 40.7 ng/mL 30 - 100")
    assert len(rows) == 1
    assert rows[0]["raw_label"] == "Vitamin D (25-OH)"
    assert rows[0]["value"] == 40.7
    assert rows[0]["unit"] == "ng/mL"
    assert rows[0]["reference_low"] == 30.0


def test_full_real_report_pattern_extracts_only_genuine_lab_rows():
    text = "\n".join([
        "AN ISO 9001:2015 CERTIFIED LABORATORY",
        "REG/REF: DWH 8515 PAGE 1 of 3",
        "Patient: Anjana AGE/GENDER 48 Yrs./Male",
        "COLL TIME 22 Aug 09:10 PRN. TIME 22 Aug 11:40",
        "LIPID PROFILE",
        "Triglycerides 217.27 mg/dL 30-200",
        "HDL Cholesterol 38.34 mg/dL 40 - 60",
        "VLDL 43 mg/dL 5 - 40",
        "HAEMATOLOGY",
        "Haemoglobin 12.2 g/dL 13-17",
        "PLAIN 460473",
        "PRINTED 22 Aug 2026 Page 1 of 3",
        "BIOCHEMISTRY",
        "Lipase 41.5 IU/L 13 - 60",
        "Serum Creatinine 0.92 mg/dL 0.6-1.3",
        "Vitamin D (25-OH) 40.7 ng/mL 30 - 100",
        "TSH 1.5097 uIU/mL 0.4 - 4.0",
        "UP TO 150 samples processed daily at this facility",
        "PRINTED 22 Aug 2026 Page 2 of 3",
    ])
    rows = parse_report_text(text)
    labels = {r["raw_label"] for r in rows}

    expected = {
        "Triglycerides", "HDL Cholesterol", "VLDL", "Haemoglobin",
        "Lipase", "Serum Creatinine", "Vitamin D (25-OH)", "TSH",
    }
    assert labels == expected

    values = {r["raw_label"]: r["value"] for r in rows}
    assert values["Triglycerides"] == 217.27
    assert values["Haemoglobin"] == 12.2
    assert values["Vitamin D (25-OH)"] == 40.7


# --- Multi-line table format: the ANJANA report's actual layout, where the
# text extraction/OCR pipeline emits each table cell (label, value, unit,
# range) as its own line rather than one combined "label value unit range"
# line. This used to produce zero rows because every existing pattern
# expected a single line per lab result. ---

def test_multiline_label_value_unit_range():
    text = "\n".join(["Haemoglobin", "12.2", "g/dL", "13 - 17"])
    rows = parse_report_text(text)
    assert len(rows) == 1
    assert rows[0]["raw_label"] == "Haemoglobin"
    assert rows[0]["value"] == 12.2
    assert rows[0]["unit"] == "g/dL"
    assert rows[0]["reference_low"] == 13.0
    assert rows[0]["reference_high"] == 17.0


def test_multiline_two_word_label():
    text = "\n".join(["Serum Triglycerides", "217.27", "mg/dL.", "30 - 200"])
    rows = parse_report_text(text)
    assert len(rows) == 1
    assert rows[0]["raw_label"] == "Serum Triglycerides"
    assert rows[0]["value"] == 217.27
    # Trailing OCR period on the unit cell is stripped.
    assert rows[0]["unit"] == "mg/dL"
    assert rows[0]["reference_high"] == 200.0


def test_multiline_comparator_only_range_less_than():
    # "<38" means the reference range is "below 38", not a two-sided range.
    text = "\n".join(["Serum Lipase", "41.5", "IU/l", "<38"])
    rows = parse_report_text(text)
    assert len(rows) == 1
    assert rows[0]["raw_label"] == "Serum Lipase"
    assert rows[0]["value"] == 41.5
    assert rows[0]["unit"] == "IU/l"
    assert rows[0]["reference_low"] is None
    assert rows[0]["reference_high"] == 38.0


def test_multiline_bare_hyphen_range_with_lowercase_unit_variant():
    text = "\n".join(["RA Factor", "3.86", "Iu/ml", "0-20"])
    rows = parse_report_text(text)
    assert len(rows) == 1
    assert rows[0]["raw_label"] == "RA Factor"
    assert rows[0]["value"] == 3.86
    assert rows[0]["reference_low"] == 0.0
    assert rows[0]["reference_high"] == 20.0


def test_multiline_decimal_range():
    text = "\n".join(["Serum TSH", "1.5097", "uIU/ml", "0.35-4.94"])
    rows = parse_report_text(text)
    assert len(rows) == 1
    assert rows[0]["raw_label"] == "Serum TSH"
    assert rows[0]["value"] == 1.5097
    assert rows[0]["reference_low"] == 0.35
    assert rows[0]["reference_high"] == 4.94


def test_multiline_vitamin_b12_pmol_unit():
    text = "\n".join(["Serum Vitamin B12", "48.6", "pmol/L", "7.1 - 124.0"])
    rows = parse_report_text(text)
    assert len(rows) == 1
    assert rows[0]["raw_label"] == "Serum Vitamin B12"
    assert rows[0]["value"] == 48.6
    assert rows[0]["reference_low"] == 7.1
    assert rows[0]["reference_high"] == 124.0


def test_multiline_all_caps_label():
    text = "\n".join(["VITAMIN D", "40.7", "ng/ml", "20-100"])
    rows = parse_report_text(text)
    assert len(rows) == 1
    assert rows[0]["raw_label"] == "VITAMIN D"
    assert rows[0]["value"] == 40.7


def test_multiline_label_with_embedded_digit_not_mistaken_for_junk():
    # "HbA1c" has a digit in the name itself -- must still be usable as a
    # multi-line label, the same way it's usable as a one-line label.
    text = "\n".join(["HbA1c", "5.4", "%", "4.0-5.6"])
    rows = parse_report_text(text)
    assert len(rows) == 1
    assert rows[0]["raw_label"] == "HbA1c"
    assert rows[0]["value"] == 5.4
    assert rows[0]["reference_low"] == 4.0
    assert rows[0]["reference_high"] == 5.6


def test_multiline_rejects_administrative_lines_between_rows():
    # The real report interleaves genuine multi-line rows with junk lines
    # (accreditation numbers, page counters, timestamps) that must not be
    # mistaken for a label, a value, a unit, or a range.
    text = "\n".join([
        "Reg/Ref: DWH-8515 / 269031",
        "Page 1 of 3",
        "Printed: 22-Aug-26 16:46:52",
        "Haemoglobin",
        "12.2",
        "g/dL",
        "13 - 17",
        "Serum Lipase",
        "41.5",
        "IU/l",
        "<38",
        "RA Factor",
        "3.86",
        "Iu/ml",
        "0-20",
    ])
    rows = parse_report_text(text)
    labels = {r["raw_label"] for r in rows}
    assert labels == {"Haemoglobin", "Serum Lipase", "RA Factor"}


def test_multiline_section_headers_produce_no_rows():
    # Section headers are text-only lines with no following number -- they
    # must not be mistaken for the start of a multi-line row.
    for header in ["HAEMATOLOGY", "LIPID PROFILE", "BIOCHEMISTRY", "Interpretation"]:
        assert parse_report_text(header) == []


def test_full_anjana_multiline_report_extracts_only_genuine_rows():
    # End-to-end regression using the actual ANJANA report's structure:
    # every real parameter on its own multi-line block, interleaved with
    # the administrative text that previously produced junk rows (9001,
    # 8515, 460473, page numbers) and caused the extractor to see zero
    # genuine parameters.
    text = "\n".join([
        "AN ISO 9001:2015 CERTIFIED LABORATORY",
        "Reg/Ref: DWH-8515 / 269031",
        "Patient: Anjana AGE/GENDER 48 Yrs./Male",
        "Printed: 22-Aug-26 16:46:52",
        "HAEMATOLOGY",
        "Haemoglobin",
        "12.2",
        "g/dL",
        "13 - 17",
        "LIPID PROFILE",
        "Serum Triglycerides",
        "217.27",
        "mg/dL.",
        "30 - 200",
        "PLAIN 460473",
        "Page 1 of 3",
        "BIOCHEMISTRY",
        "Serum Lipase",
        "41.5",
        "IU/l",
        "<38",
        "RA Factor",
        "3.86",
        "Iu/ml",
        "0-20",
        "Serum TSH",
        "1.5097",
        "uIU/ml",
        "0.35-4.94",
        "Serum Vitamin B12",
        "48.6",
        "pmol/L",
        "7.1 - 124.0",
        "VITAMIN D",
        "40.7",
        "ng/ml",
        "20-100",
        "HbA1c",
        "5.4",
        "%",
        "4.0-5.6",
        "Printed: 22-Aug-26 16:46:52",
        "Page 2 of 3",
    ])
    rows = parse_report_text(text)
    labels = {r["raw_label"] for r in rows}

    expected = {
        "Haemoglobin", "Serum Triglycerides", "Serum Lipase", "RA Factor",
        "Serum TSH", "Serum Vitamin B12", "VITAMIN D", "HbA1c",
    }
    assert labels == expected

    values = {r["raw_label"]: r["value"] for r in rows}
    assert values["Haemoglobin"] == 12.2
    assert values["Serum Triglycerides"] == 217.27
    assert values["Serum Lipase"] == 41.5
    assert values["RA Factor"] == 3.86
    assert values["Serum TSH"] == 1.5097
    assert values["Serum Vitamin B12"] == 48.6
    assert values["VITAMIN D"] == 40.7
    assert values["HbA1c"] == 5.4
