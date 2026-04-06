"""Query rewriting and lightweight domain inference."""

from __future__ import annotations

import re

_DOMAIN_KEYWORDS = {
    "health": {"med", "meds", "medication", "medications", "dose", "prescription"},
    "career": {"role", "promotion", "job", "manager"},
    "preferences": {"prefer", "preference", "diet", "dislike"},
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
    tokens = set(re.findall(r"[a-z0-9_]+", (query or "").lower()))
    if not tokens:
        return fallback
    best_domain = fallback
    best_score = 0
    for domain, keywords in _DOMAIN_KEYWORDS.items():
        score = len(tokens & keywords)
        if score > best_score:
            best_score = score
            best_domain = domain
    return best_domain
