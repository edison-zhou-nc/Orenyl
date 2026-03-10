"""Query rewriting and lightweight domain inference."""

from __future__ import annotations

import re


_DOMAIN_KEYWORDS = {
    "health": {"med", "meds", "medication", "medications", "dose", "prescription"},
    "career": {"role", "promotion", "job", "manager", "work"},
    "preferences": {"prefer", "preference", "diet", "like", "dislike"},
}

_REWRITE_MAP = {
    r"\bmeds\b": "medications",
    r"\bmed\b": "medication",
}


def rewrite_query(query: str) -> str:
    rewritten = query or ""
    for pattern, replacement in _REWRITE_MAP.items():
        rewritten = re.sub(pattern, replacement, rewritten, flags=re.IGNORECASE)
    return rewritten.strip()


def infer_domain(query: str, fallback: str = "general") -> str:
    lowered = (query or "").lower()
    for domain, keywords in _DOMAIN_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return domain
    return fallback
