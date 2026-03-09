"""Optional semantic deduplication helpers."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any


_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
    "i", "in", "is", "it", "of", "on", "or", "that", "the", "this", "to",
    "today", "was", "were", "with", "you",
}


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def _meaningful_tokens(value: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9_]+", _normalize_text(value))
    filtered = {tok for tok in tokens if tok not in _STOPWORDS and len(tok) > 1}
    return filtered or set(tokens)


def semantic_similarity(a: str, b: str) -> float:
    """Jaccard similarity over stopword-filtered tokens."""
    ta = _meaningful_tokens(a)
    tb = _meaningful_tokens(b)
    if not ta or not tb:
        return 0.0
    intersection = len(ta & tb)
    denom = max(len(ta | tb), 1)
    return intersection / denom


def is_semantic_duplicate(a: str, b: str, threshold: float = 0.92) -> bool:
    return semantic_similarity(a, b) >= threshold


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


def check_semantic_duplicate(
    db: Any,
    content: str,
    domains: list[str],
    window_hours: int = 24,
    threshold: float = 0.92,
) -> tuple[bool, str | None]:
    if not content or not domains:
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
        candidate = _event_text(event)
        if is_semantic_duplicate(content, candidate, threshold=threshold):
            return True, event.get("id")
    return False, None
