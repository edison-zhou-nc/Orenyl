"""Persistent structured audit sink for security events."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
import uuid
from datetime import UTC, datetime
from typing import Any

from . import env_vars


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _db_path() -> str:
    return os.environ.get(env_vars.AUDIT_DB_PATH, "orenyl_audit.db")


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
        # foreign_keys=ON is safe here: the only FK is security_audit_chain.event_id →
        # security_audit_events(id) ON DELETE CASCADE. Insertion order is always safe
        # (event row written before chain row in log_security_event). Deletion is handled
        # automatically by CASCADE; clear_events() deletes chain rows first as additional
        # belt-and-suspenders, not as a requirement.
        conn.execute("PRAGMA foreign_keys=ON")
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
        conn.execute(
            """CREATE TABLE IF NOT EXISTS security_audit_chain (
                   seq_id INTEGER PRIMARY KEY AUTOINCREMENT,
                   event_id INTEGER NOT NULL,
                   prev_hash TEXT NOT NULL,
                   event_hash TEXT NOT NULL,
                   chain_hash TEXT NOT NULL,
                   FOREIGN KEY (event_id) REFERENCES security_audit_events(id) ON DELETE CASCADE
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
    event_ts = _now_iso()
    event_details = details or {}
    with _LOCK:
        conn = _conn()
        event_payload = {
            "ts": event_ts,
            "action": action,
            "result": result,
            "principal_id": principal_id,
            "request_id": event_request_id,
            "details": event_details,
        }
        event_json = json.dumps(event_payload, sort_keys=True, separators=(",", ":"))
        event_hash = hashlib.sha256(event_json.encode("utf-8")).hexdigest()
        prev_row = conn.execute(
            "SELECT chain_hash FROM security_audit_chain ORDER BY seq_id DESC LIMIT 1"
        ).fetchone()
        prev_hash = str(prev_row["chain_hash"]) if prev_row is not None else ""
        chain_hash = hashlib.sha256(f"{prev_hash}{event_hash}".encode()).hexdigest()
        cursor = conn.execute(
            """INSERT INTO security_audit_events
               (ts, action, result, principal_id, request_id, details_json)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                event_ts,
                action,
                result,
                principal_id,
                event_request_id,
                json.dumps(event_details, sort_keys=True),
            ),
        )
        conn.execute(
            """INSERT INTO security_audit_chain
               (event_id, prev_hash, event_hash, chain_hash)
               VALUES (?, ?, ?, ?)""",
            (
                int(cursor.lastrowid) if cursor.lastrowid is not None else 0,
                prev_hash,
                event_hash,
                chain_hash,
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
        conn.execute("DELETE FROM security_audit_chain")
        conn.execute("DELETE FROM security_audit_events")
        conn.commit()


def verify_hash_chain() -> bool:
    with _LOCK:
        conn = _conn()
        event_count = conn.execute("SELECT COUNT(*) AS c FROM security_audit_events").fetchone()[
            "c"
        ]
        rows = conn.execute(
            """SELECT c.seq_id, c.prev_hash, c.event_hash, c.chain_hash,
                      e.ts, e.action, e.result, e.principal_id, e.request_id, e.details_json
               FROM security_audit_chain c
               JOIN security_audit_events e ON e.id = c.event_id
               ORDER BY c.seq_id ASC"""
        ).fetchall()
    if len(rows) != int(event_count):
        return False
    expected_prev = ""
    for row in rows:
        payload = {
            "ts": row["ts"],
            "action": row["action"],
            "result": row["result"],
            "principal_id": row["principal_id"],
            "request_id": row["request_id"],
            "details": json.loads(row["details_json"]),
        }
        event_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        expected_event_hash = hashlib.sha256(event_json.encode("utf-8")).hexdigest()
        if expected_event_hash != row["event_hash"]:
            return False
        if row["prev_hash"] != expected_prev:
            return False
        expected_chain_hash = hashlib.sha256(
            f"{expected_prev}{expected_event_hash}".encode()
        ).hexdigest()
        if expected_chain_hash != row["chain_hash"]:
            return False
        expected_prev = row["chain_hash"]
    return True


def _reset_for_tests() -> None:
    global _CONN
    with _LOCK:
        if _CONN is not None:
            _CONN.close()
            _CONN = None
