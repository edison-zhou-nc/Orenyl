"""Embedding-based semantic deduplication helpers."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from .embeddings import cosine_similarity

logger = logging.getLogger(__name__)

def _event_text(event_row: dict[str, Any]) -> str:
    payload = event_row.get("payload")
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            payload = {"text": payload}
    if isinstance(payload, dict):
        if payload.get("text"):
            return str(payload.get("text"))
        if payload.get("value"):
            return str(payload.get("value"))
        return json.dumps(payload, sort_keys=True)
    return str(payload or "")


def is_semantic_duplicate_by_embedding(
    candidate: list[float],
    existing: list[float],
    threshold: float = 0.92,
) -> bool:
    return cosine_similarity(candidate, existing) >= threshold


def check_semantic_duplicate(
    db: Any,
    provider: Any,
    content: str,
    domains: list[str],
    window_hours: int = 24,
    threshold: float = 0.92,
) -> tuple[bool, str | None]:
    if not content or not domains:
        return False, None

    try:
        candidate_embedding = provider.embed_text(content)
    except Exception:
        return False, None
    threshold_ts = (
        datetime.now(timezone.utc) - timedelta(hours=window_hours)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = db.get_recent_events_in_domains(domains, threshold_ts)

    for event in rows:
        existing = db.get_event_embedding(event.get("id", ""))
        existing_embedding: list[float] | None = None
        if existing is not None:
            existing_embedding = existing["vector"]
            existing_model = str(existing.get("model_id", ""))
            if existing_model != str(provider.provider_id):
                logger.warning(
                    "semantic_dedup_embedding_model_mismatch event_id=%s stored_model=%s provider=%s",
                    event.get("id"),
                    existing_model,
                    provider.provider_id,
                )
                existing_embedding = None
            elif len(existing_embedding) != len(candidate_embedding):
                logger.warning(
                    "semantic_dedup_embedding_dim_mismatch event_id=%s stored_dim=%s candidate_dim=%s",
                    event.get("id"),
                    len(existing_embedding),
                    len(candidate_embedding),
                )
                existing_embedding = None

        if existing_embedding is None:
            existing_text = _event_text(event)
            try:
                existing_embedding = provider.embed_text(existing_text)
                db.upsert_event_embedding(
                    event["id"],
                    existing_embedding,
                    provider.provider_id,
                )
            except Exception:
                continue
        if is_semantic_duplicate_by_embedding(
            candidate_embedding,
            existing_embedding,
            threshold=threshold,
        ):
            return True, event.get("id")
    return False, None
