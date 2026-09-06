import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _register_and_login(email="demo@example.com", password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password, "full_name": "Demo User"})
    login = client.post("/auth/login", json={"email": email, "password": password})
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health_status_is_public():
    resp = client.get("/health/status")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_register_and_login_flow():
    headers = _register_and_login("flow@example.com", "StrongPass123")
    resp = client.get("/patients/me", headers=headers)
    assert resp.status_code == 200


def test_login_rejects_wrong_password():
    _register_and_login("wrongpw@example.com", "StrongPass123")
    resp = client.post("/auth/login", json={"email": "wrongpw@example.com", "password": "nope"})
    assert resp.status_code == 401


def test_upload_requires_auth():
    resp = client.post("/reports/upload", files={"file": ("r.pdf", b"data", "application/pdf")})
    assert resp.status_code == 401


def test_upload_and_analyze_pipeline(monkeypatch):
    def fake_extract_and_normalize(file_bytes, filename):
        return {
            "raw_text": "Hemoglobin: 10.2 g/dL (12.0-15.5)\nFasting Glucose: 168 mg/dL (70-100)",
            "extraction_method": "test_stub",
            "rows": [
                {"raw_label": "Hemoglobin", "value": 10.2, "unit": "g/dL",
                 "reference_low": 12.0, "reference_high": 15.5, "canonical_parameter": "hemoglobin"},
                {"raw_label": "Fasting Glucose", "value": 168, "unit": "mg/dL",
                 "reference_low": 70, "reference_high": 100, "canonical_parameter": "fasting_glucose"},
            ],
        }

    monkeypatch.setattr("app.api.reports.extract_and_normalize", fake_extract_and_normalize)

    headers = _register_and_login("pipeline@example.com", "StrongPass123")

    upload_resp = client.post(
        "/reports/upload",
        headers=headers,
        files={"file": ("cbc_report.pdf", b"%PDF-1.4 fake bytes", "application/pdf")},
    )
    assert upload_resp.status_code == 200
    upload_data = upload_resp.json()
    assert upload_data["parameters_detected"] == 2
    report_id = upload_data["report_id"]

    analyze_resp = client.post(f"/reports/{report_id}/analyze", headers=headers, json={})
    assert analyze_resp.status_code == 200
    analysis = analyze_resp.json()
    assert analysis["risk"]["abnormal_count"] == 2
    assert analysis["risk"]["level"] >= 2
    assert "disclaimer" in analysis
    assert analysis["explanation"]["risk_level"] == analysis["risk"]["level"]

    get_resp = client.get(f"/reports/{report_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["risk"]["score"] == analysis["risk"]["score"]


def test_analyze_refuses_when_zero_parameters_extracted(monkeypatch):
    def fake_extract_and_normalize(file_bytes, filename):
        return {"raw_text": "", "extraction_method": "test_stub", "rows": []}

    monkeypatch.setattr("app.api.reports.extract_and_normalize", fake_extract_and_normalize)
    headers = _register_and_login("emptyupload@example.com", "StrongPass123")

    upload_resp = client.post(
        "/reports/upload", headers=headers,
        files={"file": ("blank.pdf", b"%PDF-1.4 fake bytes", "application/pdf")},
    )
    assert upload_resp.status_code == 200
    assert upload_resp.json()["parameters_detected"] == 0
    report_id = upload_resp.json()["report_id"]

    # Must NEVER silently produce a fake "healthy" result when nothing was extracted.
    analyze_resp = client.post(f"/reports/{report_id}/analyze", headers=headers, json={})
    assert analyze_resp.status_code == 422


def test_history_contains_report_metadata(monkeypatch):
    def fake_extract_and_normalize(file_bytes, filename):
        return {
            "raw_text": "Hemoglobin: 10.2 g/dL (12.0-15.5)",
            "extraction_method": "test_stub",
            "rows": [
                {
                    "raw_label": "Hemoglobin",
                    "value": 10.2,
                    "unit": "g/dL",
                    "reference_low": 12.0,
                    "reference_high": 15.5,
                    "canonical_parameter": "hemoglobin",
                }
            ],
        }

    monkeypatch.setattr(
        "app.api.reports.extract_and_normalize",
        fake_extract_and_normalize,
    )

    headers = _register_and_login(
        "history-metadata@example.com",
        "StrongPass123",
    )

    upload_resp = client.post(
        "/reports/upload",
        headers=headers,
        files={
            "file": (
                "annual_checkup.pdf",
                b"%PDF-1.4 fake bytes",
                "application/pdf",
            )
        },
    )

    assert upload_resp.status_code == 200

    report_id = upload_resp.json()["report_id"]

    analyze_resp = client.post(
        f"/reports/{report_id}/analyze",
        headers=headers,
        json={},
    )

    assert analyze_resp.status_code == 200

    history_resp = client.get(
        "/patients/me/history",
        headers=headers,
    )

    assert history_resp.status_code == 200

    history = history_resp.json()

    assert len(history) == 1

    point = history[0]

    assert point["report_id"] == report_id
    assert point["filename"] == "annual_checkup.pdf"
    assert point["score"] >= 0
    assert point["risk_label"]
    assert point["abnormal_count"] == 1
    assert point["parameters"]["hemoglobin"] == 10.2
