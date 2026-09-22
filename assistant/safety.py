"""Deterministic, non-LLM safety pieces: PII redaction, injection filtering,
and refusal copy.

PII detection/redaction runs on the user's question before it reaches
Claude at all, so sensitive input is never sent to the model, stored in
conversation history, or echoed back in an answer.

Prompt-injection *phrasing* detection also runs before Claude is called.
Classic injection attempts ("ignore previous instructions", "reveal your
system prompt") get caught and refused deterministically here rather than
left entirely to the model: Claude's safety training reliably keeps it from
actually complying with an injected instruction, but there's no
informational payoff to it also calling our `decline_to_answer` tool for
bookkeeping, so relying on that alone made the refusal *category* a coin
flip even though the refusal itself was consistent. A regex pre-filter for
the well-known phrasings closes that gap; `decline_to_answer` remains a
semantic backstop in `assistant/orchestrator.py` for paraphrased attempts
that don't match a known pattern.

Deciding WHETHER a question is off-topic or asks for opinion/legal advice
needs semantic judgment a regex can't do reliably, so that call stays with
Claude via `decline_to_answer` - but WHAT gets said back, for every refusal
category, is canned, not phrased live, so it's consistent and this module
can be tested without a model call.
"""

import re

_PII_PATTERNS = [
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("credit_card", re.compile(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b")),
    (
        "bank_account",
        re.compile(
            r"\b(?:account|routing)\s*(?:number|no\.?|#)?\s*[:#-]?\s*\d{6,17}\b",
            re.IGNORECASE,
        ),
    ),
    ("password", re.compile(r"\bpassword\s*(?:is|:|=)\s*\S+", re.IGNORECASE)),
]

_PII_LABELS = {
    "ssn": "a Social Security number",
    "credit_card": "a credit card number",
    "bank_account": "a bank account/routing number",
    "password": "a password",
}


def redact_pii(text: str) -> tuple[str, list[str]]:
    """Replace obvious sensitive info with a placeholder.

    Returns the redacted text and the list of PII categories found (empty
    if none). Patterns are checked in order and each only sees what earlier
    patterns left behind, so an overlapping span (e.g. "account number:
    4111111111111111") gets redacted once, by whichever pattern matches
    first.
    """
    found: list[str] = []
    for label, pattern in _PII_PATTERNS:

        def _sub(match, label=label):
            found.append(label)
            return f"[REDACTED-{label.upper()}]"

        text = pattern.sub(_sub, text)
    return text, found


def pii_notice(found: list[str]) -> str:
    """A user-facing heads-up that PII was stripped, to prepend to an answer."""
    kinds = sorted({_PII_LABELS.get(label, label) for label in found})
    if len(kinds) == 1:
        kinds_str = kinds[0]
    else:
        kinds_str = ", ".join(kinds[:-1]) + " and " + kinds[-1]
    return (
        f"I noticed what looks like {kinds_str} in your message and removed "
        "it before processing - please avoid sharing personal identifiers "
        "here.\n\n"
    )


_INJECTION_PATTERNS = [
    re.compile(r"ignore (?:all |any )?(?:previous|prior|above|earlier) instructions", re.IGNORECASE),
    re.compile(r"disregard (?:all |any )?(?:previous|prior|above|earlier) instructions", re.IGNORECASE),
    re.compile(r"forget (?:all |your |the )?(?:previous |prior )?instructions", re.IGNORECASE),
    re.compile(r"(?:reveal|show|print|repeat|output|what is) (?:your|the) (?:system )?prompt", re.IGNORECASE),
    re.compile(r"you are now\b", re.IGNORECASE),
    re.compile(r"pretend (?:you are|to be)\b", re.IGNORECASE),
    re.compile(r"\bdeveloper mode\b", re.IGNORECASE),
    re.compile(r"\bjailbreak\b", re.IGNORECASE),
]


def detect_prompt_injection(text: str) -> bool:
    """True if the text contains a well-known prompt-injection phrasing."""
    return any(pattern.search(text) for pattern in _INJECTION_PATTERNS)


REFUSAL_MESSAGES = {
    "off_topic": (
        "I'm scoped to Alabama campaign-finance compliance, this platform's "
        "how-to questions, political/campaign-finance terminology, and this "
        "campaign's own data. That question is outside what I can help with "
        "here."
    ),
    "opinion_or_advice": (
        "I can give you objective information - what the law says, what a "
        "term means, or what your campaign's data shows - but I can't offer "
        "a subjective opinion or legal advice about your specific situation. "
        "For that, talk to your campaign's attorney or compliance officer."
    ),
    "prompt_injection": (
        "I can't follow instructions embedded in a message, or reveal or "
        "ignore my own instructions. I'm here to help with Alabama "
        "campaign-finance compliance, this platform's how-tos, political/"
        "campaign-finance terminology, and this campaign's own data - what "
        "can I help you with in that scope?"
    ),
}

COMPLIANCE_DISCLAIMER = (
    "\n\n*This is general information about Alabama campaign-finance law, "
    "not legal advice. For guidance on your specific situation, consult "
    "your campaign's attorney or compliance officer.*"
)

_STATUTE_CITATION_RE = re.compile(
    r"§\s*\d|Ala\.?\s*Code|Code of Alabama", re.IGNORECASE
)


def cites_alabama_statute(text: str) -> bool:
    """True if the answer text itself cites an Alabama statute.

    Used to decide whether to attach COMPLIANCE_DISCLAIMER. Earlier this
    was inferred from retrieval - whether a search call's top-ranked
    passage came from a law category - but that's rank noise: a query like
    "cap on a federal committee's contribution" can rank the glossary's
    general "contribution-limit" definition above the specific statute
    that actually answers it, giving a false negative, while an unrelated
    query can drag in stray statute passages ranked just below the correct
    glossary hit, giving a false positive. Checking what the model's own
    answer actually cites is the direct signal instead of a proxy for it.
    """
    return bool(_STATUTE_CITATION_RE.search(text))
