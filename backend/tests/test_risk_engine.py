from app.risk_engine.reference_ranges import interpret_value, severity_tier
from app.risk_engine.scoring import compute_risk


def test_severity_tier_normal():
    direction, severity = severity_tier(95, 70, 100)
    assert direction == "normal"
    assert severity == 0


def test_severity_tier_mild_high():
    direction, severity = severity_tier(105, 70, 100)  # 5% over
    assert direction == "high"
    assert severity == 15


def test_severity_tier_severe_high():
    direction, severity = severity_tier(200, 70, 100)  # 100% over
    assert direction == "high"
    assert severity == 80


def test_interpret_value_prefers_report_range_over_default():
    result = interpret_value("hemoglobin", 11.5, report_low=11.0, report_high=16.0)
    assert result["flag"] == "normal"
    assert result["reference_source"] == "report-provided reference range"


def test_interpret_value_falls_back_to_default_range():
    result = interpret_value("fasting_glucose", 168)
    assert result["flag"] == "high"
    assert result["severity"] > 0
    assert result["reference_low"] == 70


def test_interpret_value_unrecognized_parameter():
    result = interpret_value(None, 42)
    assert result["flag"] == "unrecognized"
    assert result["severity"] == 0


# --- One-sided report-provided reference ranges (Bug #2) -----------------
# A lab report frequently prints only one side of a range for tests where
# only one direction is clinically meaningful (e.g. "Serum Lipase <38").
# The report's own one-sided range must be honored, not discarded in favor
# of the canonical default just because the other bound is absent.

def test_high_only_report_range_flags_high_when_over():
    # The real ANJANA case: Serum Lipase 41.5, report range is "<38".
    result = interpret_value("lipase", 41.5, report_low=None, report_high=38.0)
    assert result["flag"] == "high"
    assert result["reference_source"] == "report-provided reference range"
    assert result["reference_low"] is None
    assert result["reference_high"] == 38.0
    assert result["severity"] > 0


def test_high_only_report_range_normal_when_under():
    result = interpret_value("lipase", 20.0, report_low=None, report_high=38.0)
    assert result["flag"] == "normal"
    assert result["severity"] == 0
    assert result["reference_source"] == "report-provided reference range"


def test_low_only_report_range_flags_low_when_under():
    result = interpret_value("some_test", 5, report_low=10.0, report_high=None)
    assert result["flag"] == "low"
    assert result["reference_source"] == "report-provided reference range"
    assert result["reference_low"] == 10.0
    assert result["reference_high"] is None
    assert result["severity"] > 0


def test_low_only_report_range_normal_when_over():
    result = interpret_value("some_test", 15, report_low=10.0, report_high=None)
    assert result["flag"] == "normal"
    assert result["severity"] == 0
    assert result["reference_source"] == "report-provided reference range"


def test_two_sided_report_range_regression_unaffected():
    # Existing two-sided behavior must be identical to before this fix.
    result = interpret_value("hemoglobin", 11.5, report_low=11.0, report_high=16.0)
    assert result["flag"] == "normal"
    assert result["reference_source"] == "report-provided reference range"

    result_high = interpret_value("hemoglobin", 20.0, report_low=11.0, report_high=16.0)
    assert result_high["flag"] == "high"
    assert result_high["reference_low"] == 11.0
    assert result_high["reference_high"] == 16.0


def test_absent_report_range_still_falls_back_to_default():
    # No report_low or report_high at all -- must still use the canonical
    # default range exactly as before.
    result = interpret_value("fasting_glucose", 168)
    assert result["flag"] == "high"
    assert result["severity"] > 0
    assert result["reference_low"] == 70
    assert result["reference_source"] != "report-provided reference range"


def test_unknown_canonical_with_no_report_range_remains_unrecognized():
    # No default range exists for this canonical, and no report range was
    # given either -- must remain "unrecognized", not crash on a None bound.
    result = interpret_value("mid_cells", 7.0)
    assert result["flag"] == "unrecognized"
    assert result["severity"] == 0


def test_severity_tier_one_sided_high_only():
    direction, severity = severity_tier(41.5, None, 38.0)
    assert direction == "high"
    assert severity > 0


def test_severity_tier_one_sided_low_only():
    direction, severity = severity_tier(5, 10.0, None)
    assert direction == "low"
    assert severity > 0


def test_critical_value_forces_high_severity_and_flag():
    result = interpret_value("spo2", 82)  # below critical threshold of 90
    assert result["critical"] is True
    assert result["severity"] == 100


def test_compute_risk_all_normal_is_level_1():
    findings = [
        {"flag": "normal", "severity": 0},
        {"flag": "normal", "severity": 0},
    ]
    risk = compute_risk(findings)
    assert risk["score"] == 0
    assert risk["level"] == 1
    assert risk["abnormal_count"] == 0


def test_compute_risk_single_severe_finding_is_elevated():
    findings = [{"flag": "high", "severity": 80, "critical": False}]
    risk = compute_risk(findings)
    assert risk["level"] >= 3
    assert risk["abnormal_count"] == 1


def test_compute_risk_critical_breach_forces_level_5():
    findings = [
        {"flag": "low", "severity": 100, "critical": True},
        {"flag": "normal", "severity": 0},
    ]
    risk = compute_risk(findings)
    assert risk["level"] == 5
    assert risk["critical_breach"] is True
    assert risk["score"] >= 90


def test_compute_risk_is_monotonic_with_more_abnormal_findings():
    few = compute_risk([{"flag": "high", "severity": 35, "critical": False}])
    many = compute_risk([{"flag": "high", "severity": 35, "critical": False}] * 4)
    assert many["score"] >= few["score"]
