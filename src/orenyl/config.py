"""Runtime configuration helpers."""

from __future__ import annotations

import os

from . import env_vars


def _require_clean_env() -> None:
    env_vars.require_no_legacy_env_vars()


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return default


def _float_env(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def semantic_dedup_threshold_for_domains(domains: list[str]) -> float:
    _require_clean_env()
    default = _float_env(env_vars.SEMANTIC_DEDUP_THRESHOLD_DEFAULT, 0.92)
    # For multi-domain events, choose the highest configured cutoff so
    # dedup behavior is deterministic and conservative.
    overrides: list[float] = []
    for domain in domains:
        key = f"{env_vars.SEMANTIC_DEDUP_THRESHOLD_PREFIX}{(domain or '').strip().upper()}"
        override = _float_env(key, -1.0)
        if override >= 0.0:
            overrides.append(override)
    best = max(overrides) if overrides else default
    return max(0.0, min(best, 1.0))


def min_fact_confidence_threshold() -> float:
    _require_clean_env()
    value = _float_env(env_vars.MIN_FACT_CONFIDENCE, 0.7)
    return max(0.0, min(value, 1.0))


def multi_tenant_enabled() -> bool:
    _require_clean_env()
    return os.environ.get(env_vars.ENABLE_MULTI_TENANT, "0").strip() == "1"


def dev_stdio_mode_enabled() -> bool:
    _require_clean_env()
    return (
        os.environ.get(env_vars.TRANSPORT, "streamable-http").strip().lower() == "stdio"
        and os.environ.get(env_vars.ALLOW_STDIO_DEV, "0").strip() == "1"
    )


def auth_required_for_runtime() -> bool:
    return not dev_stdio_mode_enabled()


def vector_backend_name() -> str:
    _require_clean_env()
    return os.environ.get(env_vars.VECTOR_BACKEND, "local").strip().lower() or "local"


def pgvector_dsn() -> str:
    _require_clean_env()
    return os.environ.get(env_vars.PGVECTOR_DSN, "").strip()


def compliance_strict_mode_enabled() -> bool:
    _require_clean_env()
    return _bool_env(env_vars.COMPLIANCE_STRICT_MODE, default=True)


def read_only_mode_enabled() -> bool:
    _require_clean_env()
    return _bool_env(env_vars.READ_ONLY_MODE, default=False)
