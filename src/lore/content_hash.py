"""Content hashing primitives for dedupe."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta, timezone
from typing import Any


def compute_content_hash(content: str) -> str:
    normalized = re.sub(r"\s+", " ", (content or "").strip().lower())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def check_duplicate(db: Any, content_hash: str, domains: list[str], window_hours: int = 24) -> bool:
    if not content_hash or not domains:
        return False
    # Dedup window is based on event occurrence time (events.ts), not insertion time.
    # This preserves deterministic replay behavior but can be affected by backdated events.
    threshold = (
        datetime.now(timezone.utc) - timedelta(hours=window_hours)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    placeholders = ",".join("?" for _ in domains)
    row = db.conn.execute(
        f"""SELECT COUNT(DISTINCT e.id)
            FROM events e
            JOIN event_domains ed ON ed.event_id = e.id
            WHERE e.deleted_at IS NULL
              AND e.content_hash = ?
              AND e.ts >= ?
              AND ed.domain IN ({placeholders})""",
        (content_hash, threshold, *domains),
    ).fetchone()
    return int(row[0] or 0) > 0
