"""Ingestion policy filters for noisy or sensitive input."""

from __future__ import annotations

import re

SENSITIVE_PATTERNS = [
    re.compile(r"password:", re.I),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\bsk-[a-z0-9]+\b", re.I),
    re.compile(r"\bghp_[a-z0-9]+\b", re.I),
    re.compile(r"\bxoxb-[a-z0-9-]+\b", re.I),
    re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),
]

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
