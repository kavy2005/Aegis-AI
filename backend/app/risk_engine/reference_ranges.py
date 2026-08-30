"""
Reference ranges used ONLY when a report does not supply its own range.

If the uploaded report includes a lab-provided reference range, the risk
engine always prefers that range -- see interpret_value() below. These
defaults exist purely so the demo/prototype can still classify a value
when no report range is available.

Source: general adult reference intervals commonly published by clinical
laboratories, entered here for prototype purposes only. This has NOT been
independently validated for clinical use -- see README "Limitations".
"""
from typing import Optional, Tuple

REFERENCE_SOURCE = "AEGIS AI default adult reference set v0.1 (prototype, not clinically validated)"

# canonical_parameter -> {"male": (low, high), "female": (low, high), "default": (low, high)}
DEFAULT_REFERENCE_RANGES = {
    "hemoglobin": {"male": (13.0, 17.0), "female": (12.0, 15.5), "default": (12.0, 17.0)},
    "rbc": {"male": (4.5, 5.9), "female": (4.0, 5.2), "default": (4.0, 5.9)},
    "wbc": {"default": (4.0, 11.0)},
    "platelets": {"default": (150, 450)},
    "hematocrit": {"male": (38.8, 50.0), "female": (34.9, 44.5), "default": (34.9, 50.0)},
    "mcv": {"default": (80, 100)},
    "mch": {"default": (27, 33)},
    "mchc": {"default": (32, 36)},
    "neutrophils": {"default": (40, 75)},
    "lymphocytes": {"default": (20, 45)},
    "mpv": {"default": (7.5, 11.5)},
    "rdw": {"default": (11.5, 14.5)},
    "rdw_sd": {"default": (39, 46)},
    # mid_cells, plcr, pdw, pct: deliberately no default here -- these
    # platelet/differential indices vary meaningfully by analyzer brand
    # and method, with no consistent cross-lab "normal adult range" the
    # way ALT or creatinine have. Classified only when the report supplies
    # its own reference range; otherwise left as "unrecognized" rather than
    # guessing a number that isn't backed by a clear convention.
    "fasting_glucose": {"default": (70, 100)},
    "random_glucose": {"default": (70, 140)},
    "hba1c": {"default": (4.0, 5.6)},
    "total_cholesterol": {"default": (0, 200)},
    "ldl": {"default": (0, 130)},
    "hdl": {"male": (40, 999), "female": (50, 999), "default": (40, 999)},
    "triglycerides": {"default": (0, 150)},
    "vldl": {"default": (5, 40)},
    "creatinine": {"male": (0.7, 1.3), "female": (0.6, 1.1), "default": (0.6, 1.3)},
    "bun": {"default": (7, 20)},
    "urea": {"default": (15, 45)},
    "uric_acid": {"male": (3.4, 7.0), "female": (2.4, 6.0), "default": (2.4, 7.0)},
    "egfr": {"default": (90, 200)},
    "alt": {"default": (7, 56)},
    "ast": {"default": (8, 48)},
    "alp": {"default": (44, 147)},
    "bilirubin": {"default": (0.1, 1.2)},
    "albumin": {"default": (3.5, 5.0)},
    "sodium": {"default": (135, 145)},
    "potassium": {"default": (3.5, 5.1)},
    "calcium": {"default": (8.5, 10.5)},
    "systolic_bp": {"default": (90, 120)},
    "diastolic_bp": {"default": (60, 80)},
    "heart_rate": {"default": (60, 100)},
    "spo2": {"default": (95, 100)},
    "temperature": {"default": (97.0, 99.0)},
    "respiratory_rate": {"default": (12, 20)},
    "bmi": {"default": (18.5, 24.9)},
    "lipase": {"default": (13, 60)},
    "amylase": {"default": (23, 85)},
    "vitamin_d": {"default": (30, 100)},
    "vitamin_b12": {"default": (200, 900)},
    "tsh": {"default": (0.4, 4.0)},
    "t3": {"default": (80, 200)},
    "t4": {"default": (5.0, 12.0)},
    "crp": {"default": (0, 5)},
    "ra_factor": {"default": (0, 14)},
}

# Breaching these bounds marks a finding as clinically "critical" regardless
# of how the overall score works out -- deliberately narrow, deliberately
# conservative safety-net values, not a diagnostic claim.
CRITICAL_THRESHOLDS = {
    "spo2": {"low": 90},
    "heart_rate": {"low": 40, "high": 130},
    "systolic_bp": {"low": 80, "high": 180},
    "diastolic_bp": {"low": 40, "high": 120},
    "temperature": {"high": 103.0},
    "fasting_glucose": {"low": 54, "high": 400},
    "random_glucose": {"low": 54, "high": 400},
    "potassium": {"low": 2.5, "high": 6.5},
    "sodium": {"low": 120, "high": 160},
}


def get_reference_range(
    canonical: str, sex: Optional[str] = None
) -> Optional[Tuple[float, float]]:
    entry = DEFAULT_REFERENCE_RANGES.get(canonical)
    if not entry:
        return None
    if sex and sex.lower() in entry:
        return entry[sex.lower()]
    return entry.get("default")


def is_critical(canonical: str, value: float) -> bool:
    bounds = CRITICAL_THRESHOLDS.get(canonical)
    if not bounds:
        return False
    if "low" in bounds and value < bounds["low"]:
        return True
    if "high" in bounds and value > bounds["high"]:
        return True
    return False


def severity_tier(value: float, low: Optional[float], high: Optional[float]) -> Tuple[str, int]:
    """Return (direction, severity 0-100) for a value against a range.

    Either bound may be None for a one-sided range -- the report-provided
    "<38" or ">10" style range a lab prints when only one direction is
    clinically meaningful for that test. At least one of low/high must be
    given; callers (interpret_value) already guard against both being None
    by returning "unrecognized" before this is called.
    """
    if low is not None and high is not None:
        if low <= value <= high:
            return "normal", 0
        if value > high:
            deviation = (value - high) / high if high > 0 else 1.0
            direction = "high"
        else:
            deviation = (low - value) / low if low > 0 else 1.0
            direction = "low"
    elif high is not None:
        # One-sided "less than X" range: no lower bound was provided, so
        # there's nothing to flag as "low" -- only an excess over the
        # upper bound is a deviation.
        if value <= high:
            return "normal", 0
        deviation = (value - high) / high if high > 0 else 1.0
        direction = "high"
    else:
        # One-sided "greater than X" range: no upper bound was provided.
        if value >= low:
            return "normal", 0
        deviation = (low - value) / low if low > 0 else 1.0
        direction = "low"

    if deviation < 0.10:
        severity = 15
    elif deviation < 0.30:
        severity = 35
    elif deviation < 0.60:
        severity = 55
    else:
        severity = 80
    return direction, severity


def interpret_value(
    canonical: Optional[str],
    value: float,
    report_low: Optional[float] = None,
    report_high: Optional[float] = None,
    sex: Optional[str] = None,
):
    """
    Decide which range to use (report-provided range wins), then classify
    the value against it. Returns a dict describing the finding.

    A report-provided range is honored even when only one side is given
    (e.g. lab prints "<38" with no lower bound, or ">10" with no upper
    bound) -- that is itself the report's real reference range, not a
    partial/broken one, and discarding it in favor of the canonical
    default would silently override what the lab actually printed.
    """
    source = None
    low, high = None, None

    if report_low is not None or report_high is not None:
        low, high = report_low, report_high
        source = "report-provided reference range"
    elif canonical:
        default_range = get_reference_range(canonical, sex)
        if default_range:
            low, high = default_range
            source = REFERENCE_SOURCE

    if low is None and high is None:
        return {
            "flag": "unrecognized",
            "severity": 0,
            "reference_low": None,
            "reference_high": None,
            "reference_source": None,
            "critical": False,
        }

    direction, severity = severity_tier(value, low, high)
    critical = canonical is not None and is_critical(canonical, value)
    if critical:
        severity = 100

    return {
        "flag": direction,
        "severity": severity,
        "reference_low": low,
        "reference_high": high,
        "reference_source": source,
        "critical": critical,
    }
