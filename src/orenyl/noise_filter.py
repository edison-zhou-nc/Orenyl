"""Ingestion policy filters for noisy or sensitive input."""

from __future__ import annotations

import re

SENSITIVE_PATTERNS = [
    re.compile(r"password:", re.I),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bsk-[a-z0-9]+\b", re.I),
    re.compile(r"\bghp_[a-z0-9]+\b", re.I),
    re.compile(r"\bxoxb-[a-z0-9-]+\b", re.I),
    re.compile(r"-----BEGIN(?:\s+(?:RSA|EC|DSA))?\s+PRIVATE KEY-----", re.I),
    re.compile(r"\beyJ[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{6,}\b"),
    re.compile(r"\bbearer\s+[A-Za-z0-9._-]{20,}\b", re.I),
    re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    re.compile(r"\b(?:\+?\d{1,2}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?){2}\d{4}\b"),
    re.compile(r"\b(?:postgres(?:ql)?|mysql|redis|mongodb):\/\/\S+:\S+@\S+\/\S+\b", re.I),
]

# Heuristic phrase filters. These are intentionally conservative and can miss
# semantic variants; they are a best-effort guardrail, not a classifier.
REFUSAL_PATTERNS = [
    re.compile(r"\bi don't have enough information\b", re.I),
    re.compile(r"\bi cannot answer that\b", re.I),
    re.compile(r"\bi'm unable to\b", re.I),
]


def should_store(content: str) -> tuple[bool, str]:
    text = (content or "").strip()
    if len(text) < 10:
        return False, "too_short"
    for pattern in REFUSAL_PATTERNS:
        if pattern.search(text):
            return False, "agent_refusal_or_meta"
    for pattern in SENSITIVE_PATTERNS:
        if pattern.search(text):
            return False, "sensitive_credential_or_identifier"
    return True, "ok"


def contains_sensitive_identifier(content: str) -> bool:
    text = (content or "").strip()
    for pattern in SENSITIVE_PATTERNS:
        if pattern.search(text):
            return True
    return False
