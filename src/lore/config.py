"""Runtime configuration helpers."""

from __future__ import annotations

import os


def _float_env(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def semantic_dedup_threshold_for_domains(domains: list[str]) -> float:
    default = _float_env("LORE_SEMANTIC_DEDUP_THRESHOLD_DEFAULT", 0.92)
    # For multi-domain events, choose the highest configured cutoff so
    # dedup behavior is deterministic and conservative.
    overrides: list[float] = []
    for domain in domains:
        key = f"LORE_SEMANTIC_DEDUP_THRESHOLD_{(domain or '').strip().upper()}"
        override = _float_env(key, -1.0)
        if override >= 0.0:
            overrides.append(override)
    best = max(overrides) if overrides else default
    return max(0.0, min(best, 1.0))


def min_fact_confidence_threshold() -> float:
    value = _float_env("LORE_MIN_FACT_CONFIDENCE", 0.7)
    return max(0.0, min(value, 1.0))


def multi_tenant_enabled() -> bool:
    return os.environ.get("LORE_ENABLE_MULTI_TENANT", "0").strip() == "1"


def vector_backend_name() -> str:
    return os.environ.get("LORE_VECTOR_BACKEND", "local").strip().lower() or "local"


def pgvector_dsn() -> str:
    return os.environ.get("LORE_PGVECTOR_DSN", "").strip()
