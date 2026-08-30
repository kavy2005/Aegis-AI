from app.risk_engine.parameter_dictionary import normalize_label


def test_common_hemoglobin_aliases():
    assert normalize_label("Hemoglobin") == "hemoglobin"
    assert normalize_label("Haemoglobin") == "hemoglobin"
    assert normalize_label("Hb") == "hemoglobin"
    assert normalize_label("HGB") == "hemoglobin"


def test_case_and_whitespace_insensitive():
    assert normalize_label("  hEmoglobin  ") == "hemoglobin"
    assert normalize_label("hgb:") == "hemoglobin"


def test_glucose_context_disambiguation():
    assert normalize_label("Fasting Blood Glucose") == "fasting_glucose"
    assert normalize_label("Random Blood Sugar") == "random_glucose"
    assert normalize_label("HbA1c") == "hba1c"
    assert normalize_label("Glycated Hemoglobin") == "hba1c"
    # No qualifier -> documented default
    assert normalize_label("Glucose") == "fasting_glucose"


def test_lipid_and_kidney_aliases():
    assert normalize_label("LDL Cholesterol") == "ldl"
    assert normalize_label("SGPT") == "alt"
    assert normalize_label("S. Creatinine") == "creatinine"


def test_unrecognized_label_returns_none():
    assert normalize_label("Some Totally Unknown Test") is None
    assert normalize_label("") is None
    assert normalize_label(None) is None


def test_real_report_parameters_previously_missing_from_dictionary():
    # Regression: these six were extracted as rows but had no canonical
    # mapping, so they were always scored as "unrecognized" (severity 0)
    # regardless of how abnormal the actual value was.
    assert normalize_label("VLDL") == "vldl"
    assert normalize_label("Lipase") == "lipase"
    assert normalize_label("Vitamin D (25-OH)") == "vitamin_d"
    assert normalize_label("TSH") == "tsh"
    assert normalize_label("CRP") == "crp"
    assert normalize_label("RA Factor") == "ra_factor"


# --- MCH vs Hemoglobin regression -----------------------------------------
# "MCH (Mean Corpus. Haemoglobin)" was being normalized to "hemoglobin"
# because its parenthetical expansion contains the substring "haemoglobin",
# an alias of the hemoglobin canonical, and the hemoglobin dictionary entry
# is iterated before mch's during the generic substring fallback.

def test_mch_with_parenthetical_expansion_does_not_become_hemoglobin():
    assert normalize_label("MCH (Mean Corpus. Haemoglobin)") == "mch"
    assert normalize_label("MCH") == "mch"
    assert normalize_label("Mean Corpuscular Hemoglobin") == "mch"


def test_mchc_still_resolves_correctly_and_is_not_confused_with_mch():
    assert normalize_label("MCHC (Mean Corpus. Hb Conc.)") == "mchc"
    assert normalize_label("MCHC") == "mchc"


def test_hemoglobin_still_resolves_correctly_after_mch_fix():
    # The fix must not regress plain Hemoglobin itself.
    assert normalize_label("Haemoglobin") == "hemoglobin"
    assert normalize_label("Hemoglobin") == "hemoglobin"
    assert normalize_label("Hb") == "hemoglobin"


# --- ANJANA report: 16 previously-unrecognized real-world labels ----------

def test_anjana_previously_unrecognized_labels_now_resolve():
    assert normalize_label("Neutrophils") == "neutrophils"
    assert normalize_label("Lymphocytes") == "lymphocytes"
    assert normalize_label("Mid") == "mid_cells"
    assert normalize_label("LPCR") == "plcr"
    assert normalize_label("MPV") == "mpv"
    assert normalize_label("PDW") == "pdw"
    assert normalize_label("PCT") == "pct"
    assert normalize_label("MCV (Mean Cell Volume)") == "mcv"
    assert normalize_label("RDWA") == "rdw_sd"
    assert normalize_label("RDW") == "rdw"
    assert normalize_label("Serum Uric Acid") == "uric_acid"
    assert normalize_label("Serum Amylase") == "amylase"
    assert normalize_label("Serum T3") == "t3"
    assert normalize_label("Serum T4") == "t4"
    assert normalize_label("Serum TSH") == "tsh"
    assert normalize_label("Serum Vitamin B12") == "vitamin_b12"


def test_anjana_full_normalization_pass_matches_real_report_labels():
    # Every raw label observed in the actual ANJANA report, recognized (OK)
    # or not, checked together as one regression covering the whole report.
    raw_labels = {
        "Haemoglobin": "hemoglobin",
        "MCH (Mean Corpus. Haemoglobin)": "mch",
        "MCHC (Mean Corpus. Hb Conc.)": "mchc",
        "HCT ( hematocrit )": "hematocrit",
        "Serum Bilirubin, Total": "bilirubin",
        "SGOT": "ast",
        "SGPT": "alt",
        "Serum Urea": "urea",
        "Serum Creatinine": "creatinine",
        "HbA1c": "hba1c",
        "Serum Cholesterol": "total_cholesterol",
        "Serum Triglycerides": "triglycerides",
        "HDL Cholesterol": "hdl",
        "LDL Cholesterol": "ldl",
        "VLDL Cholesterol": "vldl",
        "Serum Calcium, Total": "calcium",
        "CRP": "crp",
        "Serum Lipase": "lipase",
        "RA Factor": "ra_factor",
        "VITAMIN D": "vitamin_d",
        "Neutrophils": "neutrophils",
        "Lymphocytes": "lymphocytes",
        "Mid": "mid_cells",
        "LPCR": "plcr",
        "MPV": "mpv",
        "PDW": "pdw",
        "PCT": "pct",
        "MCV (Mean Cell Volume)": "mcv",
        "RDWA": "rdw_sd",
        "RDW": "rdw",
        "Serum Uric Acid": "uric_acid",
        "Serum Amylase": "amylase",
        "Serum T3": "t3",
        "Serum T4": "t4",
        "Serum TSH": "tsh",
        "Serum Vitamin B12": "vitamin_b12",
    }
    for raw_label, expected_canonical in raw_labels.items():
        assert normalize_label(raw_label) == expected_canonical, (
            f"{raw_label!r} -> expected {expected_canonical!r}, "
            f"got {normalize_label(raw_label)!r}"
        )
