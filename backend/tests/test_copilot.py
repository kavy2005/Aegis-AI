import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ai.copilot import SYSTEM_PROMPT

client = TestClient(app)


def _register_and_login(email="copilot@example.com", password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password, "full_name": "Copilot User"})
    login = client.post("/auth/login", json={"email": email, "password": password})
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


SAMPLE_CONTEXT = {
    "filename": "cbc_report.pdf",
    "risk": {
        "score": 42, "level": 3, "label": "Moderate Risk / Medical Consultation Recommended",
        "abnormal_count": 1, "critical_breach": False, "summary": "One finding needs attention.",
    },
    "parameters": [
        {"raw_label": "Serum Triglycerides", "canonical_parameter": "triglycerides", "value": 217.27,
         "unit": "mg/dL", "reference_low": 30, "reference_high": 200, "reference_source": "report-provided reference range",
         "flag": "high", "severity": 15},
    ],
    "explanation": {"summary": "One finding needs attention.", "abnormal_findings": ["Serum Triglycerides"],
                     "risk_level": 3, "explanation": [], "recommended_next_steps": [], "urgent_warning": None},
}


def test_copilot_requires_auth():
    resp = client.post("/copilot/chat", json={"message": "Why is my triglyceride high?"})
    assert resp.status_code == 401


def test_copilot_accepts_a_question_with_report_context():
    headers = _register_and_login()
    resp = client.post(
        "/copilot/chat",
        headers=headers,
        json={"message": "Why is my triglyceride high?", "report_context": SAMPLE_CONTEXT},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "reply" in data and isinstance(data["reply"], str) and data["reply"]
    assert data["source"] in ("llm", "rule_based")
    assert "disclaimer" in data


def test_copilot_report_context_is_actually_used_in_fallback_reply():
    # With no ANTHROPIC_API_KEY set in the test environment, the deterministic
    # fallback runs -- it must reflect the specific report data given, not a
    # generic canned string, proving report_context is actually passed through.
    headers = _register_and_login("contextcheck@example.com")
    resp = client.post(
        "/copilot/chat",
        headers=headers,
        json={"message": "What should I know?", "report_context": SAMPLE_CONTEXT},
    )
    assert resp.status_code == 200
    reply = resp.json()["reply"]
    assert "217.27" in reply
    assert "Moderate Risk" in reply or "42" in reply


def test_copilot_handles_missing_report_context_gracefully():
    headers = _register_and_login("nocontext@example.com")
    resp = client.post(
        "/copilot/chat",
        headers=headers,
        json={"message": "What does my hemoglobin mean?"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "upload" in data["reply"].lower() or "analyz" in data["reply"].lower()


def test_copilot_survives_llm_failure_without_crashing(monkeypatch):
    headers = _register_and_login("llmfailure@example.com")
    monkeypatch.setattr("app.ai.copilot.settings.ANTHROPIC_API_KEY", "fake-key-for-test")

    def _boom(message, report_context, history):
        raise RuntimeError("simulated Anthropic API outage")

    monkeypatch.setattr("app.ai.copilot._call_anthropic_chat", _boom)

    resp = client.post(
        "/copilot/chat",
        headers=headers,
        json={"message": "Why is my triglyceride high?", "report_context": SAMPLE_CONTEXT},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "rule_based"
    assert "217.27" in data["reply"]


def test_copilot_system_prompt_contains_medical_safety_guardrails():
    lowered = SYSTEM_PROMPT.lower()
    assert "diagnose" in lowered
    assert "prescribe" in lowered or "medication" in lowered
    assert "healthcare professional" in lowered or "doctor" in lowered


# --- Fallback is question-aware, not one generic canned reply -------------
# Different questions must get different, relevant answers even with no
# ANTHROPIC_API_KEY set, so the offline demo path doesn't look broken.

def test_fallback_gives_distinct_answers_to_distinct_questions():
    headers = _register_and_login("distinctanswers@example.com")

    def ask(message):
        resp = client.post("/copilot/chat", headers=headers, json={"message": message, "report_context": SAMPLE_CONTEXT})
        assert resp.status_code == 200
        return resp.json()["reply"]

    r1 = ask("Why is my triglyceride high?")
    r2 = ask("What should I discuss with my doctor?")
    r3 = ask("Should I start taking medication for this?")
    r4 = ask("What changed compared to my previous report?")

    replies = {r1, r2, r3, r4}
    assert len(replies) == 4, "distinct questions must not all produce the identical canned reply"


def test_fallback_medication_question_never_recommends_medication():
    headers = _register_and_login("medicationsafety@example.com")
    resp = client.post(
        "/copilot/chat", headers=headers,
        json={"message": "What medication should I take for this?", "report_context": SAMPLE_CONTEXT},
    )
    reply = resp.json()["reply"].lower()
    assert "can't recommend" in reply or "cannot recommend" in reply
    assert "healthcare professional" in reply


def test_fallback_previous_report_comparison_is_explicitly_unavailable():
    headers = _register_and_login("comparisoncheck@example.com")
    resp = client.post(
        "/copilot/chat", headers=headers,
        json={"message": "What changed compared with my previous report?", "report_context": SAMPLE_CONTEXT},
    )
    reply = resp.json()["reply"].lower()
    assert "don't have a previous report" in reply or "can't tell you what's changed" in reply


def test_fallback_answers_about_the_specific_mentioned_parameter():
    headers = _register_and_login("paramspecific@example.com")
    resp = client.post(
        "/copilot/chat", headers=headers,
        json={"message": "Why is my triglyceride high?", "report_context": SAMPLE_CONTEXT},
    )
    reply = resp.json()["reply"]
    assert "triglycerides" in reply.lower()
    assert "217.27" in reply
    assert "30" in reply and "200" in reply
