"""Input guardrails: reject or clean user requests before they reach retrieval."""

import re
from dataclasses import dataclass

MAX_QUERY_CHARS = 300
MIN_QUERY_CHARS = 2

# Phrases that try to steer the system itself instead of describing music taste.
INJECTION_PATTERNS = [
    r"ignore (all |any )?(previous|prior|above) (instructions|rules)",
    r"disregard (the |your )?(instructions|rules|system)",
    r"(reveal|show|print) (your |the )?(system )?prompt",
    r"you are now",
    r"developer mode",
]
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


@dataclass
class GuardrailResult:
    """Outcome of validating one request."""
    ok: bool
    cleaned: str
    reason: str = ""


def validate_query(text: object) -> GuardrailResult:
    """Return ok=True with a cleaned query, or ok=False with a human-readable reason."""
    if not isinstance(text, str):
        return GuardrailResult(False, "", "request must be text")
    cleaned = _CONTROL_CHARS.sub(" ", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) < MIN_QUERY_CHARS:
        return GuardrailResult(False, "", "request is empty; describe a mood, activity, or genre")
    if len(cleaned) > MAX_QUERY_CHARS:
        return GuardrailResult(False, "", f"request is too long ({len(cleaned)} > {MAX_QUERY_CHARS} chars)")
    lowered = cleaned.lower()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, lowered):
            return GuardrailResult(False, "", "request looks like an instruction to the system, not a music request")
    return GuardrailResult(True, cleaned)
