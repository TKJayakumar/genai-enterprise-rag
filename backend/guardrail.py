"""
Evaluator / Guardrail node.

'Checks output against a policy, quality bar, or safety rule.'
Evaluation criteria (from the challenge brief): ensure the response is
accurate, policy-compliant, and includes source citations.

Kept rule-based (fast, deterministic, no extra LLM call) but structured
so an LLM-as-judge call could be swapped in later.
"""
import re

DENYLIST_PHRASES = [
    "i don't know your policy",
    "as an ai language model",
    "i cannot verify",
]


def validate(answer: str, allowed_docs) -> dict:
    reasons = []

    has_citation = bool(re.search(r"\[\d+\]", answer)) or any(
        doc["title"].lower() in answer.lower() for doc in allowed_docs
    )
    if not has_citation:
        reasons.append("Missing source citation.")

    if not allowed_docs:
        reasons.append("No authorized source documents were available to ground the answer.")

    lowered = answer.lower()
    for phrase in DENYLIST_PHRASES:
        if phrase in lowered:
            reasons.append(f"Contains disallowed phrase: '{phrase}'.")

    if len(answer.strip()) < 15:
        reasons.append("Response too short to be a substantive, policy-compliant answer.")

    passed = len(reasons) == 0
    return {"passed": passed, "reasons": reasons}
