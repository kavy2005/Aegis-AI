"""
Optional LLM-backed explanation.

The rule-based engine in risk_engine/explanation.py is the source of truth
and always runs. This module can OPTIONALLY ask an LLM to restate that
same structured data in friendlier prose -- the LLM is only ever given
already-decided findings and told to reformat them, never asked to decide
risk itself. If ANTHROPIC_API_KEY isn't set, or the call fails or returns
invalid JSON, we silently fall back to the rule-based explanation so the
product still works with zero external dependencies.
"""
import json
from typing import Dict

from app.config import settings

SYSTEM_PROMPT = """You are a medical-report explanation formatter for AEGIS AI.
You are given ALREADY-DECIDED structured findings (parameter, value, flag, risk level).
Do NOT invent new medical facts, do NOT change the risk level, do NOT diagnose.
Rewrite the given findings into a warmer, clearer plain-language explanation.
Respond with ONLY valid JSON matching this exact shape, nothing else:
{"summary": str, "abnormal_findings": [str], "risk_level": int, "explanation": [{"parameter": str, "value": number, "unit": str, "flag": str, "why_it_matters": str}], "recommended_next_steps": [str], "urgent_warning": str or null}
"""


def _call_anthropic(structured_findings: Dict) -> Dict:
    import anthropic

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": json.dumps(structured_findings)}],
    )
    text = "".join(block.text for block in message.content if getattr(block, "type", None) == "text")
    return json.loads(text)


def _validate_shape(data: Dict) -> bool:
    required = {"summary", "abnormal_findings", "risk_level", "explanation", "recommended_next_steps"}
    return isinstance(data, dict) and required.issubset(data.keys())


def get_explanation(structured_findings: Dict, rule_based_fallback: Dict) -> Dict:
    """
    structured_findings: the same input the rule-based engine used (findings + risk).
    rule_based_fallback: the already-computed rule-based explanation dict, used
    verbatim whenever the LLM path is unavailable or returns something malformed.
    """
    if not settings.ANTHROPIC_API_KEY:
        return {**rule_based_fallback, "source": "rule_based"}

    try:
        llm_result = _call_anthropic(structured_findings)
        if _validate_shape(llm_result):
            llm_result.setdefault("urgent_warning", rule_based_fallback.get("urgent_warning"))
            return {**llm_result, "source": "llm"}
    except Exception:
        pass

    return {**rule_based_fallback, "source": "rule_based"}
