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
