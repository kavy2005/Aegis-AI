"""
AEGIS AI Copilot: a chat interface over ONE already-analyzed report.

Reuses the same LLM integration pattern as app/ai/explain.py -- same
Anthropic client, same settings.ANTHROPIC_API_KEY check, same philosophy of
never letting the LLM path being unavailable break the product. The
difference is shape, not mechanism: explain.py restates a fixed set of
findings once; this module answers open-ended follow-up questions about
those same findings, optionally across a short conversation history.

The Copilot is deliberately NOT asked to interpret the raw report text or
decide risk itself -- it is only ever given the structured output the
rule-based risk engine already computed (parameters, flags, severities,
reference ranges, overall score/level/summary) and asked to explain and
discuss THAT. This keeps the same "LLM reformats, never decides" boundary
explain.py already established, extended to a conversational setting.

If ANTHROPIC_API_KEY isn't set, or the call fails for any reason (network,
rate limit, malformed response), we fall back to a deterministic templated
reply built directly from the structured report context, so the chat UI
never crashes or hangs even with zero external dependencies configured.
"""
import json
import re
from typing import Dict, List, Optional

from app.config import settings

SYSTEM_PROMPT = """You are the AEGIS AI Copilot, embedded in the AEGIS AI app, helping a user \
understand a lab report that AEGIS's own rule-based risk engine has ALREADY analyzed.

You are given, as your only source of truth, the structured findings that engine already \
computed for this specific report: each parameter's label, canonical name, value, unit, \
reference range, flag (normal/high/low/unrecognized), severity, and the overall risk \
score/level/summary. Always ground your answers in this data. Never invent a value, reference \
range, flag, or prior report that was not given to you -- if something wasn't provided (for \
example, a previous report to compare against), say so plainly instead of guessing.

Safety rules, with no exceptions:
- Never diagnose a disease or medical condition. You may describe in general terms what a \
marker can indicate, but never assert the user has a specific condition.
- Never prescribe, and never recommend starting, stopping, or changing any medication or dose.
- Never claim certainty about a medical situation.
- You are not a substitute for a doctor. For any question touching medication, treatment, or \
diagnosis, give safe general information only and clearly recommend the user speak with a \
qualified healthcare professional.
- If the report's own risk assessment flags something as critical, or the overall score/level \
indicates a severe or urgent result, calmly and clearly recommend prompt medical evaluation \
rather than trying to independently assess the emergency yourself.

Style: warm, clear, plain language, concise -- a few short paragraphs at most. This is a \
hackathon prototype, not a diagnostic tool; stay within the disclaimer already shown elsewhere \
in the product."""


def _build_system_prompt(report_context: Optional[Dict]) -> str:
    if report_context and report_context.get("parameters"):
        context_json = json.dumps(report_context, default=str)
        context_block = f"\n\nSTRUCTURED REPORT CONTEXT (source of truth, JSON):\n{context_json}"
    else:
        context_block = (
            "\n\nNo analyzed report is currently available in this conversation. If the user "
            "asks about a report, tell them they need to upload and analyze one first."
        )
    return SYSTEM_PROMPT + context_block


def _call_anthropic_chat(message: str, report_context: Optional[Dict], history: Optional[List[Dict]]) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    messages = []
    for turn in (history or []):
        role, content = turn.get("role"), turn.get("content")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": message})

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=700,
        system=_build_system_prompt(report_context),
        messages=messages,
    )
    text = "".join(block.text for block in response.content if getattr(block, "type", None) == "text")
    return text.strip()


def _significant_words(text: str) -> set:
    """Lowercased words, trailing 's' stripped so plural/singular forms of a
    parameter name (e.g. "triglyceride" vs "triglycerides") still match,
    short/noise words dropped."""
    return {w.rstrip("s") for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2}


def _find_mentioned_parameter(message: str, parameters: List[Dict]) -> Optional[Dict]:
    """Best-matching parameter whose canonical name or raw label shares a
    word with the user's message, e.g. "triglyceride" in the message
    matches the "triglycerides" canonical name. Returns None if nothing in
    the message plausibly refers to any parameter in this report."""
    message_words = _significant_words(message)
    if not message_words:
        return None

    best_score, best_param = 0, None
    for p in parameters:
        for candidate in (p.get("canonical_parameter"), p.get("raw_label")):
            if not candidate:
                continue
            candidate_words = _significant_words(candidate.replace("_", " "))
            overlap = candidate_words & message_words
            score = sum(len(w) for w in overlap)  # longer/more-specific words count more
            if score > best_score:
                best_score, best_param = score, p
    return best_param


_MEDICATION_KEYWORDS = ("medicat", "medicine", "prescri", "dosage", "dose", "treat", "cure",
                         "diagnos", "drug", "pill", "statin", "supplement", "should i take", "should i start")
_DOCTOR_KEYWORDS = ("doctor", "discuss", "physician", "appointment")
_COMPARISON_KEYWORDS = ("previous", "last report", "last time", "compare", "compared", "changed since")

_OFFLINE_NOTE = (
    "(I'm currently running without a connected AI service, so this is a structured summary "
    "rather than a tailored answer to your exact wording.)"
)
_SAFETY_NOTE = (
    "For medication, treatment, or diagnosis questions, please talk to a qualified healthcare "
    "professional -- I'm not able to prescribe or diagnose."
)


def _format_parameter_line(p: Dict) -> str:
    name = p.get("canonical_parameter") or p.get("raw_label")
    ref_low, ref_high = p.get("reference_low"), p.get("reference_high")
    ref = f"{ref_low if ref_low is not None else '?'}-{ref_high if ref_high is not None else '?'}"
    return f"- {name}: {p.get('value')} {p.get('unit') or ''} ({p.get('flag')}, reference {ref})"


def _rule_based_reply(message: str, report_context: Optional[Dict]) -> str:
    """Deterministic, template-based fallback used whenever the LLM path is
    unavailable. It never tries to interpret arbitrary free text -- instead
    it does light keyword/parameter-name matching against the message so
    common real questions (a named parameter, "my doctor", "previous
    report", medication/diagnosis questions) each get a distinct, relevant
    answer grounded only in the structured report data, rather than one
    identical canned reply for every question."""
    if not report_context or not report_context.get("parameters"):
        return (
            "I don't have an analyzed report to reference yet. Please upload and analyze a lab "
            "report first, then come back and ask me about it."
        )

    risk = report_context.get("risk") or {}
    parameters = report_context.get("parameters") or []
    abnormal = [p for p in parameters if p.get("flag") in ("high", "low")]
    lowered = message.lower()

    risk_line = (
        f'Your last AEGIS analysis came back as "{risk.get("label", "")}" ({risk.get("score", "?")}/100).'
        if risk else "No overall risk summary is available for this report."
    )

    # Medication/diagnosis/treatment intent is checked first, and always
    # short-circuits -- this is the one guardrail that must never be
    # skipped in favor of a more specific-looking answer.
    if any(kw in lowered for kw in _MEDICATION_KEYWORDS):
        return (
            f"I can't recommend, start, stop, or change any medication, and I can't diagnose a "
            f"condition. {_SAFETY_NOTE} What I can share structurally: {risk_line} {_OFFLINE_NOTE}"
        )

    if any(kw in lowered for kw in _COMPARISON_KEYWORDS):
        return (
            "I don't have a previous report to compare this one against in this conversation, "
            "so I can't tell you what's changed. I can only describe this single analysis: "
            f"{risk_line} {_OFFLINE_NOTE}"
        )

    mentioned = _find_mentioned_parameter(message, parameters)
    if mentioned:
        name = mentioned.get("canonical_parameter") or mentioned.get("raw_label")
        flag = mentioned.get("flag")
        value, unit = mentioned.get("value"), mentioned.get("unit") or ""
        ref_low, ref_high = mentioned.get("reference_low"), mentioned.get("reference_high")
        ref = f"{ref_low if ref_low is not None else '?'}-{ref_high if ref_high is not None else '?'}"
        if flag in ("high", "low"):
            return (
                f"Your {name} came back at {value} {unit}, which AEGIS flagged as {flag} against "
                f"a reference range of {ref} {unit}. {_SAFETY_NOTE} {_OFFLINE_NOTE}"
            )
        if flag == "normal":
            return (
                f"Your {name} was {value} {unit}, within the reference range of {ref} {unit} -- "
                f"no concern flagged for this one. {_OFFLINE_NOTE}"
            )
        return (
            f"AEGIS extracted {name} as {value} {unit} but didn't have a way to classify it "
            f"against a reference range for this report. {_OFFLINE_NOTE}"
        )

    if any(kw in lowered for kw in _DOCTOR_KEYWORDS):
        if abnormal:
            names = ", ".join(p.get("canonical_parameter") or p.get("raw_label") for p in abnormal[:6])
            return f"Worth bringing up with your doctor: {names}. {_SAFETY_NOTE} {_OFFLINE_NOTE}"
        return (
            f"Nothing in this report was flagged outside range, so there's nothing urgent from "
            f"this data alone to raise proactively -- but always mention any symptoms you're "
            f"having, regardless of what the numbers show. {_OFFLINE_NOTE}"
        )

    # Default: a structured overview -- covers "explain my abnormal results",
    # "give me a simple summary", and anything else not matched above.
    lines = [risk_line]
    if abnormal:
        lines.append("Parameters outside the reference range:")
        lines.extend(_format_parameter_line(p) for p in abnormal[:8])
    else:
        lines.append("All parameters in this report were within their reference ranges.")
    lines.append(f"{_OFFLINE_NOTE} {_SAFETY_NOTE}")
    return "\n".join(lines)


def get_copilot_reply(
    message: str,
    report_context: Optional[Dict],
    history: Optional[List[Dict]] = None,
) -> Dict:
    """
    message: the user's latest question.
    report_context: dict shaped like {"filename", "risk", "parameters", "explanation"} --
        the same structured output already produced by the risk engine, passed straight
        from the frontend's already-fetched analysis response. May be None/empty if no
        report has been analyzed yet.
    history: optional prior turns as [{"role": "user"|"assistant", "content": str}, ...].
    """
    if not settings.ANTHROPIC_API_KEY:
        return {"reply": _rule_based_reply(message, report_context), "source": "rule_based"}

    try:
        reply = _call_anthropic_chat(message, report_context, history)
        if reply:
            return {"reply": reply, "source": "llm"}
    except Exception:
        pass

    return {"reply": _rule_based_reply(message, report_context), "source": "rule_based"}
