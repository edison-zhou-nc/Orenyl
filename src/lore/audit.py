"""Persistent structured audit sink for security events."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _db_path() -> str:
    return os.environ.get("LORE_AUDIT_DB_PATH", "lore_audit.db")


_LOCK = threading.RLock()
_CONN: sqlite3.Connection | None = None


def _conn() -> sqlite3.Connection:
    global _CONN
    with _LOCK:
        if _CONN is not None:
            return _CONN
        conn = sqlite3.connect(_db_path(), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute(
            """CREATE TABLE IF NOT EXISTS security_audit_events (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   ts TEXT NOT NULL,
                   action TEXT NOT NULL,
                   result TEXT NOT NULL,
                   principal_id TEXT NOT NULL,
                   request_id TEXT NOT NULL,
                   details_json TEXT NOT NULL
               )"""
        )
        conn.commit()
        _CONN = conn
        return conn


def log_security_event(
    action: str,
    result: str,
    principal_id: str = "",
    request_id: str = "",
    details: dict[str, Any] | None = None,
) -> None:
    event_request_id = (request_id or "").strip() or f"req:{uuid.uuid4().hex[:12]}"
    with _LOCK:
        conn = _conn()
        conn.execute(
            """INSERT INTO security_audit_events
               (ts, action, result, principal_id, request_id, details_json)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                _now_iso(),
                action,
                result,
                principal_id,
                event_request_id,
                json.dumps(details or {}, sort_keys=True),
            ),
        )
        conn.commit()


def get_events(limit: int | None = None) -> list[dict[str, Any]]:
    query = (
        "SELECT ts, action, result, principal_id, request_id, details_json "
        "FROM security_audit_events ORDER BY id ASC"
    )
    params: tuple[Any, ...] = ()
    if isinstance(limit, int) and limit > 0:
        query += " LIMIT ?"
        params = (limit,)
    with _LOCK:
        conn = _conn()
        rows = conn.execute(query, params).fetchall()
    result: list[dict[str, Any]] = []
    for row in rows:
        result.append(
            {
                "ts": row["ts"],
                "action": row["action"],
                "result": row["result"],
                "principal_id": row["principal_id"],
                "request_id": row["request_id"],
                "details": json.loads(row["details_json"]),
            }
        )
    return result


def clear_events() -> None:
    with _LOCK:
        conn = _conn()
        conn.execute("DELETE FROM security_audit_events")
        conn.commit()
