"""Domain normalization helpers."""

from __future__ import annotations

CORE_DOMAINS = {
    "health",
    "career",
    "finance",
    "relationships",
    "preferences",
    "decisions",
}

DOMAIN_ALIASES = {
    "medical": "health",
    "wellness": "health",
    "job": "career",
    "money": "finance",
}


def normalize_domain(raw_domain: str) -> str:
    domain = (raw_domain or "").strip().lower()
    if not domain:
        return "general"
    return DOMAIN_ALIASES.get(domain, domain)


def should_promote_domain(event_count: int, threshold: int = 10) -> bool:
    return event_count >= threshold
