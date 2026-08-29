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
