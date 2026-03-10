"""Embedding-based semantic deduplication helpers."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from .embeddings import cosine_similarity

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
    domains_json = json.dumps(domains)
    rows = db.conn.execute(
        """SELECT DISTINCT e.*
            FROM events e
            JOIN event_domains ed ON ed.event_id = e.id
            WHERE e.deleted_at IS NULL
              AND e.ts >= ?
              AND ed.domain IN (SELECT value FROM json_each(?))
            ORDER BY e.ts DESC""",
        (threshold_ts, domains_json),
    ).fetchall()

    for row in rows:
        event = dict(row)
        existing = db.get_event_embedding(event.get("id", ""))
        if existing is not None:
            existing_embedding = existing["vector"]
        else:
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
