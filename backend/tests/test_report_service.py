from app.services.report_service import analyze_findings


def test_none_value_row_does_not_misalign_subsequent_findings():
    """
    Regression test for a bug where analyze_findings() skipped rows with a
    None value entirely instead of keeping the findings list positionally
    aligned with the input rows. reports.py zips report.parameters against
    result["findings"] by position (zip(report.parameters, result["findings"])),
    so a skipped/dropped entry here silently shifted every subsequent
    finding onto the wrong parameter.

    This must FAIL against the old (skip-based) implementation and PASS
    against the fixed (placeholder-based) one.
    """
    rows = [
        {"raw_label": "Parameter A", "canonical_parameter": "hemoglobin",
         "value": 10.0, "unit": "g/dL", "reference_low": None, "reference_high": None},
        {"raw_label": "Parameter B (no value)", "canonical_parameter": None,
         "value": None, "unit": None, "reference_low": None, "reference_high": None},
        {"raw_label": "Parameter C", "canonical_parameter": "fasting_glucose",
         "value": 200.0, "unit": "mg/dL", "reference_low": None, "reference_high": None},
    ]

    result = analyze_findings(rows)
    findings = result["findings"]

    # Old implementation returned only 2 findings here (B silently dropped) --
    # that length mismatch is exactly what caused the zip() misassignment.
    assert len(findings) == len(rows) == 3

    assert findings[0]["raw_label"] == "Parameter A"
    assert findings[0]["value"] == 10.0

    assert findings[1]["raw_label"] == "Parameter B (no value)"
    assert findings[1]["value"] is None
    assert findings[1]["flag"] == "unrecognized"
    assert findings[1]["severity"] == 0

    # The critical assertion: Parameter C's own finding must land at index 2
    # (its own position), not get shifted into index 1's slot the way the
    # old skip-based code effectively did for every entry after a skip.
    assert findings[2]["raw_label"] == "Parameter C"
    assert findings[2]["value"] == 200.0
    assert findings[2]["flag"] == "high"  # 200 mg/dL fasting glucose is genuinely high


def test_none_value_row_is_excluded_from_scoring_and_explanation():
    """The placeholder finding must not affect risk score or abnormal_findings --
    only alignment should change, never scoring behavior."""
    rows = [
        {"raw_label": "Parameter B (no value)", "canonical_parameter": None,
         "value": None, "unit": None, "reference_low": None, "reference_high": None},
        {"raw_label": "Fasting Glucose", "canonical_parameter": "fasting_glucose",
         "value": 200.0, "unit": "mg/dL", "reference_low": None, "reference_high": None},
    ]

    result = analyze_findings(rows)

    assert result["risk"]["abnormal_count"] == 1
    assert result["explanation"]["abnormal_findings"] == ["fasting_glucose"]
