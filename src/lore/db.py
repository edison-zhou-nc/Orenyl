"""SQLite database layer for Lore governed memory."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .models import Event, Fact, Edge, Tombstone

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


class Database:
    def __init__(self, db_path: str = ":memory:"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._in_transaction = False
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()

    def _maybe_commit(self):
        if not self._in_transaction:
            self.conn.commit()

    @contextmanager
    def transaction(self):
        if self._in_transaction:
            yield
            return
        self._in_transaction = True
        self.conn.execute("BEGIN")
        try:
            yield
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        finally:
            self._in_transaction = False

    def _init_schema(self):
        # Bring legacy v1 tables up to minimum shape before executing schema script
        # so index creation on new columns cannot fail.
        self.migrate_v1_to_v2()
        schema = SCHEMA_PATH.read_text()
        self.conn.executescript(schema)
        # Ensure uniqueness is enforced for existing DBs upgraded prior to this index.
        self.conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_facts_key_version_unique ON facts(key, version)"
        )

    def detect_schema_version(self) -> str:
        tables = {
            row[0]
            for row in self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        if {"event_domains", "domain_registry", "checkpoints"} <= tables:
            return "v2"
        return "v1"

    def migrate_v1_to_v2(self) -> None:
        def _safe_add_column(sql: str) -> None:
            try:
                self.conn.execute(sql)
            except sqlite3.OperationalError as exc:
                if "duplicate column name" in str(exc).lower():
                    return
                raise

        tables = {
            row[0]
            for row in self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        if "events" in tables:
            event_cols = {
                row[1] for row in self.conn.execute("PRAGMA table_info(events)").fetchall()
            }
            if "content_hash" not in event_cols:
                _safe_add_column("ALTER TABLE events ADD COLUMN content_hash TEXT")
            if "sensitivity" not in event_cols:
                _safe_add_column(
                    "ALTER TABLE events ADD COLUMN sensitivity TEXT NOT NULL DEFAULT 'medium'"
                )
            if "consent_source" not in event_cols:
                _safe_add_column(
                    "ALTER TABLE events ADD COLUMN consent_source TEXT NOT NULL DEFAULT 'implicit'"
                )
            if "expires_at" not in event_cols:
                _safe_add_column("ALTER TABLE events ADD COLUMN expires_at TEXT")
            if "metadata" not in event_cols:
                _safe_add_column(
                    "ALTER TABLE events ADD COLUMN metadata TEXT NOT NULL DEFAULT '{}'"
                )
            if "agent_id" not in event_cols:
                _safe_add_column("ALTER TABLE events ADD COLUMN agent_id TEXT")
            if "session_id" not in event_cols:
                _safe_add_column("ALTER TABLE events ADD COLUMN session_id TEXT")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_events_agent_id ON events(agent_id)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_events_session_id ON events(session_id)")

        if "facts" in tables:
            fact_cols = {
                row[1] for row in self.conn.execute("PRAGMA table_info(facts)").fetchall()
            }
            if "transform_config" not in fact_cols:
                _safe_add_column(
                    "ALTER TABLE facts ADD COLUMN transform_config TEXT NOT NULL DEFAULT '{}'"
                )
            if "stale" not in fact_cols:
                _safe_add_column("ALTER TABLE facts ADD COLUMN stale INTEGER NOT NULL DEFAULT 0")
            if "importance" not in fact_cols:
                _safe_add_column(
                    "ALTER TABLE facts ADD COLUMN importance REAL NOT NULL DEFAULT 0.5"
                )

        self.conn.commit()

    def close(self):
        self.conn.close()

    # ── Events ──────────────────────────────────────────────

    def insert_event(self, event: Event) -> str:
        self.conn.execute(
            """INSERT INTO events (
                   id, type, payload, content_hash, sensitivity, consent_source, expires_at, metadata,
                   agent_id, session_id, source, ts, valid_from, valid_to, created_at
               )
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event.id,
                event.type,
                json.dumps(event.payload),
                event.content_hash,
                event.sensitivity,
                event.consent_source,
                event.expires_at,
                json.dumps(event.metadata),
                event.metadata.get("agent_id"),
                event.metadata.get("session_id"),
                event.source,
                event.ts,
                event.valid_from,
                event.valid_to,
                event.created_at,
            ),
        )
        for domain in event.domains:
            self.conn.execute(
                "INSERT OR IGNORE INTO event_domains (event_id, domain) VALUES (?, ?)",
                (event.id, domain),
            )
        self._maybe_commit()
        return event.id

    def get_event(self, event_id: str) -> dict | None:
        row = self.conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        if row is None:
            return None
        d = dict(row)
        d["payload"] = json.loads(d["payload"])
        d["metadata"] = json.loads(d["metadata"])
        d["domains"] = [
            r[0]
            for r in self.conn.execute(
                "SELECT domain FROM event_domains WHERE event_id = ? ORDER BY domain",
                (event_id,),
            ).fetchall()
        ]
        return d

    def find_event_by_content_hash(self, content_hash: str) -> dict | None:
        if not content_hash:
            return None
        row = self.conn.execute(
            "SELECT id FROM events WHERE content_hash = ? AND deleted_at IS NULL ORDER BY ts DESC LIMIT 1",
            (content_hash,),
        ).fetchone()
        if row is None:
            return None
        return self.get_event(row["id"])

    def get_active_events(self, event_type: str | None = None) -> list[dict]:
        if event_type:
            rows = self.conn.execute(
                "SELECT * FROM events WHERE deleted_at IS NULL AND type = ? ORDER BY ts",
                (event_type,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM events WHERE deleted_at IS NULL ORDER BY ts"
            ).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["payload"] = json.loads(d["payload"])
            d["metadata"] = json.loads(d["metadata"])
            d["domains"] = [
                r[0]
                for r in self.conn.execute(
                    "SELECT domain FROM event_domains WHERE event_id = ? ORDER BY domain",
                    (d["id"],),
                ).fetchall()
            ]
            result.append(d)
        return result

    def get_all_events(self, event_type: str | None = None) -> list[dict]:
        if event_type:
            rows = self.conn.execute(
                "SELECT * FROM events WHERE type = ? ORDER BY ts",
                (event_type,),
            ).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM events ORDER BY ts").fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["payload"] = json.loads(d["payload"])
            d["metadata"] = json.loads(d["metadata"])
            d["domains"] = [
                r[0]
                for r in self.conn.execute(
                    "SELECT domain FROM event_domains WHERE event_id = ? ORDER BY domain",
                    (d["id"],),
                ).fetchall()
            ]
            result.append(d)
        return result

    def get_active_events_by_domains(self, domains: list[str]) -> list[dict]:
        normalized = [d.strip().lower() for d in domains if d and d.strip()]
        if not normalized:
            return self.get_active_events()
        placeholders = ",".join("?" for _ in normalized)
        rows = self.conn.execute(
            f"""SELECT DISTINCT e.*
                FROM events e
                LEFT JOIN event_domains ed ON ed.event_id = e.id
                WHERE e.deleted_at IS NULL
                  AND ed.domain IN ({placeholders})
                ORDER BY e.ts""",
            tuple(normalized),
        ).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["payload"] = json.loads(d["payload"])
            d["metadata"] = json.loads(d["metadata"])
            d["domains"] = [
                r[0]
                for r in self.conn.execute(
                    "SELECT domain FROM event_domains WHERE event_id = ? ORDER BY domain",
                    (d["id"],),
                ).fetchall()
            ]
            result.append(d)
        return result

    def get_events_by_domains(self, domains: list[str], include_tombstoned: bool = False) -> list[dict]:
        normalized = [d.strip().lower() for d in domains if d and d.strip()]
        if not normalized:
            return self.get_all_events() if include_tombstoned else self.get_active_events()
        placeholders = ",".join("?" for _ in normalized)
        deleted_clause = "" if include_tombstoned else "AND e.deleted_at IS NULL"
        rows = self.conn.execute(
            f"""SELECT DISTINCT e.*
                FROM events e
                JOIN event_domains ed ON ed.event_id = e.id
                WHERE ed.domain IN ({placeholders})
                {deleted_clause}
                ORDER BY e.ts""",
            tuple(normalized),
        ).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["payload"] = json.loads(d["payload"])
            d["metadata"] = json.loads(d["metadata"])
            d["domains"] = [
                r[0]
                for r in self.conn.execute(
                    "SELECT domain FROM event_domains WHERE event_id = ? ORDER BY domain",
                    (d["id"],),
                ).fetchall()
            ]
            result.append(d)
        return result

    def count_events_by_domains(self, domains: list[str], include_tombstoned: bool = False) -> int:
        normalized = [d.strip().lower() for d in domains if d and d.strip()]
        if not normalized:
            if include_tombstoned:
                row = self.conn.execute("SELECT COUNT(*) FROM events").fetchone()
            else:
                row = self.conn.execute(
                    "SELECT COUNT(*) FROM events WHERE deleted_at IS NULL"
                ).fetchone()
            return int(row[0] or 0)

        placeholders = ",".join("?" for _ in normalized)
        deleted_clause = "" if include_tombstoned else "AND e.deleted_at IS NULL"
        row = self.conn.execute(
            f"""SELECT COUNT(DISTINCT e.id)
                FROM events e
                JOIN event_domains ed ON ed.event_id = e.id
                WHERE ed.domain IN ({placeholders})
                {deleted_clause}""",
            tuple(normalized),
        ).fetchone()
        return int(row[0] or 0)

    def list_events_page(
        self,
        domains: list[str],
        include_tombstoned: bool,
        limit: int,
        offset: int,
    ) -> list[dict]:
        safe_limit = max(1, int(limit))
        safe_offset = max(0, int(offset))
        normalized = [d.strip().lower() for d in domains if d and d.strip()]

        if not normalized:
            deleted_clause = "" if include_tombstoned else "WHERE e.deleted_at IS NULL"
            rows = self.conn.execute(
                f"""SELECT e.*
                    FROM events e
                    {deleted_clause}
                    ORDER BY e.ts
                    LIMIT ? OFFSET ?""",
                (safe_limit, safe_offset),
            ).fetchall()
        else:
            placeholders = ",".join("?" for _ in normalized)
            deleted_clause = "" if include_tombstoned else "AND e.deleted_at IS NULL"
            rows = self.conn.execute(
                f"""SELECT DISTINCT e.*
                    FROM events e
                    JOIN event_domains ed ON ed.event_id = e.id
                    WHERE ed.domain IN ({placeholders})
                    {deleted_clause}
                    ORDER BY e.ts
                    LIMIT ? OFFSET ?""",
                (*normalized, safe_limit, safe_offset),
            ).fetchall()

        result = []
        for row in rows:
            d = dict(row)
            d["payload"] = json.loads(d["payload"])
            d["metadata"] = json.loads(d["metadata"])
            d["domains"] = [
                r[0]
                for r in self.conn.execute(
                    "SELECT domain FROM event_domains WHERE event_id = ? ORDER BY domain",
                    (d["id"],),
                ).fetchall()
            ]
            result.append(d)
        return result

    def get_event_count(self, domain: str = "general") -> int:
        if domain and domain != "general":
            row = self.conn.execute(
                """SELECT COUNT(DISTINCT e.id)
                   FROM events e
                   JOIN event_domains ed ON ed.event_id = e.id
                   WHERE e.deleted_at IS NULL AND ed.domain = ?""",
                (domain,),
            ).fetchone()
            return int(row[0] or 0)
        row = self.conn.execute(
            "SELECT COUNT(*) FROM events WHERE deleted_at IS NULL"
        ).fetchone()
        return int(row[0] or 0)

    def get_latest_event_ts(self, domain: str = "general") -> str | None:
        if domain and domain != "general":
            row = self.conn.execute(
                """SELECT MAX(e.ts)
                   FROM events e
                   JOIN event_domains ed ON ed.event_id = e.id
                   WHERE e.deleted_at IS NULL AND ed.domain = ?""",
                (domain,),
            ).fetchone()
            return row[0]
        row = self.conn.execute(
            "SELECT MAX(ts) FROM events WHERE deleted_at IS NULL"
        ).fetchone()
        return row[0]

    def get_expired_events(self, now_iso_ts: str) -> list[dict]:
        rows = self.conn.execute(
            """SELECT * FROM events
               WHERE deleted_at IS NULL
                 AND expires_at IS NOT NULL
                 AND expires_at <= ?
               ORDER BY expires_at ASC""",
            (now_iso_ts,),
        ).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["payload"] = json.loads(d["payload"])
            d["domains"] = [
                r[0]
                for r in self.conn.execute(
                    "SELECT domain FROM event_domains WHERE event_id = ? ORDER BY domain",
                    (d["id"],),
                ).fetchall()
            ]
            result.append(d)
        return result

    def soft_delete_event(self, event_id: str, deleted_at: str) -> bool:
        cur = self.conn.execute(
            "UPDATE events SET deleted_at = ? WHERE id = ? AND deleted_at IS NULL",
            (deleted_at, event_id),
        )
        self._maybe_commit()
        return cur.rowcount > 0

    def hard_delete_event(self, event_id: str) -> bool:
        self.conn.execute("DELETE FROM event_domains WHERE event_id = ?", (event_id,))
        cur = self.conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
        self._maybe_commit()
        return cur.rowcount > 0

    def update_event_payload(self, event_id: str, payload: dict[str, Any]) -> bool:
        cur = self.conn.execute(
            "UPDATE events SET payload = ? WHERE id = ?",
            (json.dumps(payload), event_id),
        )
        self._maybe_commit()
        return cur.rowcount > 0

    # ── Facts ───────────────────────────────────────────────

    def insert_fact(self, fact: Fact) -> str:
        self.conn.execute(
            """INSERT INTO facts (
                   id, key, value, transform_config, stale, importance,
                   version, rule_id, valid_from, valid_to, created_at
               )
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                fact.id,
                fact.key,
                json.dumps(fact.value),
                json.dumps(fact.transform_config),
                int(fact.stale),
                fact.importance,
                fact.version,
                fact.rule_id,
                fact.valid_from,
                fact.valid_to,
                fact.created_at,
            ),
        )
        self._maybe_commit()
        return fact.id

    def get_current_facts(self, key: str | None = None) -> list[dict]:
        """Get all valid, non-invalidated facts (optionally filtered by key)."""
        if key:
            rows = self.conn.execute(
                """SELECT * FROM facts
                   WHERE invalidated_at IS NULL AND key = ?
                   ORDER BY version DESC""",
                (key,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                """SELECT * FROM facts
                   WHERE invalidated_at IS NULL
                   ORDER BY key, version DESC"""
            ).fetchall()
        result = []
        seen_keys: set[str] = set()
        for row in rows:
            d = dict(row)
            d["value"] = json.loads(d["value"])
            d["transform_config"] = json.loads(d["transform_config"])
            d["stale"] = bool(d["stale"])
            # Only return latest version per key
            if d["key"] not in seen_keys:
                seen_keys.add(d["key"])
                result.append(d)
        return result

    def get_current_facts_by_domain(
        self,
        domain: str,
        agent_id: str = "",
        session_id: str = "",
    ) -> list[dict]:
        scoped = bool(agent_id or session_id)
        if (not domain or domain == "general") and not scoped:
            return self.get_current_facts()
        if domain and domain != "general":
            rows = self.conn.execute(
                """SELECT DISTINCT f.*
                   FROM facts f
                   WHERE f.invalidated_at IS NULL
                     AND EXISTS (
                         SELECT 1
                         FROM edges e
                         JOIN event_domains ed ON ed.event_id = e.parent_id
                         WHERE e.child_id = f.id
                           AND e.parent_type = 'event'
                           AND ed.domain = ?
                     )
                     AND NOT EXISTS (
                         SELECT 1
                         FROM edges e2
                         JOIN events ev2 ON ev2.id = e2.parent_id
                         WHERE e2.child_id = f.id
                           AND e2.parent_type = 'event'
                           AND (
                               (NULLIF(?, '') IS NOT NULL AND COALESCE(ev2.agent_id, '') <> ?)
                               OR (NULLIF(?, '') IS NOT NULL AND COALESCE(ev2.session_id, '') <> ?)
                           )
                     )
                   ORDER BY f.key, f.version DESC""",
                (domain, agent_id, agent_id, session_id, session_id),
            ).fetchall()
        else:
            rows = self.conn.execute(
                """SELECT DISTINCT f.*
                   FROM facts f
                   WHERE f.invalidated_at IS NULL
                     AND EXISTS (
                         SELECT 1
                         FROM edges e
                         WHERE e.child_id = f.id
                           AND e.parent_type = 'event'
                     )
                     AND NOT EXISTS (
                         SELECT 1
                         FROM edges e2
                         JOIN events ev2 ON ev2.id = e2.parent_id
                         WHERE e2.child_id = f.id
                           AND e2.parent_type = 'event'
                           AND (
                               (NULLIF(?, '') IS NOT NULL AND COALESCE(ev2.agent_id, '') <> ?)
                               OR (NULLIF(?, '') IS NOT NULL AND COALESCE(ev2.session_id, '') <> ?)
                           )
                     )
                   ORDER BY f.key, f.version DESC""",
                (agent_id, agent_id, session_id, session_id),
            ).fetchall()
        result = []
        seen_keys: set[str] = set()
        for row in rows:
            d = dict(row)
            d["value"] = json.loads(d["value"])
            d["transform_config"] = json.loads(d["transform_config"])
            d["stale"] = bool(d["stale"])
            if d["key"] not in seen_keys:
                seen_keys.add(d["key"])
                result.append(d)
        return result

    def get_fact(self, fact_id: str) -> dict | None:
        row = self.conn.execute("SELECT * FROM facts WHERE id = ?", (fact_id,)).fetchone()
        if row is None:
            return None
        d = dict(row)
        d["value"] = json.loads(d["value"])
        d["transform_config"] = json.loads(d["transform_config"])
        d["stale"] = bool(d["stale"])
        return d

    def get_latest_version(self, key: str) -> int:
        row = self.conn.execute(
            "SELECT MAX(version) as max_v FROM facts WHERE key = ?", (key,)
        ).fetchone()
        return row["max_v"] or 0

    def invalidate_fact(self, fact_id: str, reason: str, invalidated_at: str) -> bool:
        cur = self.conn.execute(
            """UPDATE facts SET invalidated_at = ?, invalidation_reason = ?
               WHERE id = ? AND invalidated_at IS NULL""",
            (invalidated_at, reason, fact_id),
        )
        self._maybe_commit()
        return cur.rowcount > 0

    def get_facts_by_key(self, key: str) -> list[dict]:
        """Get all versions of facts for a key (including invalidated)."""
        rows = self.conn.execute(
            "SELECT * FROM facts WHERE key = ? ORDER BY version", (key,)
        ).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["value"] = json.loads(d["value"])
            d["transform_config"] = json.loads(d["transform_config"])
            d["stale"] = bool(d["stale"])
            result.append(d)
        return result

    # ── Edges ───────────────────────────────────────────────

    def insert_edge(self, edge: Edge):
        self.conn.execute(
            """INSERT INTO edges (parent_id, parent_type, child_id, child_type, relation)
               VALUES (?, ?, ?, ?, ?)""",
            (edge.parent_id, edge.parent_type, edge.child_id, edge.child_type, edge.relation),
        )
        self._maybe_commit()

    def get_children(self, parent_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM edges WHERE parent_id = ?", (parent_id,)
        ).fetchall()
        return [dict(row) for row in rows]

    def get_parents(self, child_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM edges WHERE child_id = ?", (child_id,)
        ).fetchall()
        return [dict(row) for row in rows]

    def get_downstream_facts(self, item_id: str) -> list[str]:
        """Recursively find all downstream fact IDs from a given item."""
        visited: set[str] = set()
        queue = [item_id]
        result: list[str] = []

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            children = self.get_children(current)
            for child in children:
                child_id = child["child_id"]
                if child_id not in visited:
                    result.append(child_id)
                    queue.append(child_id)

        return result

    def delete_edges_for_item(self, item_id: str) -> int:
        cur = self.conn.execute(
            "DELETE FROM edges WHERE parent_id = ? OR child_id = ?",
            (item_id, item_id),
        )
        self._maybe_commit()
        return cur.rowcount

    def hard_delete_facts_by_source(self, event_id: str) -> int:
        rows = self.conn.execute(
            "SELECT child_id FROM edges WHERE parent_id = ? AND parent_type = 'event'",
            (event_id,),
        ).fetchall()
        fact_ids = [row[0] for row in rows]
        deleted = 0
        for fact_id in fact_ids:
            self.delete_edges_for_item(fact_id)
            cur = self.conn.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
            deleted += cur.rowcount
        self._maybe_commit()
        return deleted

    def mark_facts_stale(self, fact_ids: list[str]) -> int:
        if not fact_ids:
            return 0
        placeholders = ",".join("?" for _ in fact_ids)
        cur = self.conn.execute(
            f"UPDATE facts SET stale = 1 WHERE id IN ({placeholders})",
            tuple(fact_ids),
        )
        self._maybe_commit()
        return cur.rowcount

    def run_vacuum(self) -> None:
        self.conn.execute("VACUUM")

    # ── Tombstones ──────────────────────────────────────────

    def insert_tombstone(self, tombstone: Tombstone):
        self.conn.execute(
            """INSERT INTO tombstones (target_id, target_type, reason, deleted_at, cascade_invalidated)
               VALUES (?, ?, ?, ?, ?)""",
            (
                tombstone.target_id, tombstone.target_type, tombstone.reason,
                tombstone.deleted_at, json.dumps(tombstone.cascade_invalidated),
            ),
        )
        self._maybe_commit()

    def get_tombstones(self, target_id: str | None = None) -> list[dict]:
        if target_id:
            rows = self.conn.execute(
                "SELECT * FROM tombstones WHERE target_id = ?", (target_id,)
            ).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM tombstones").fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["cascade_invalidated"] = json.loads(d["cascade_invalidated"])
            result.append(d)
        return result

    # ── Retrieval Logs ──────────────────────────────────────

    def log_retrieval(self, query: str, context_pack: str, trace: str):
        self.conn.execute(
            "INSERT INTO retrieval_logs (query, context_pack, trace) VALUES (?, ?, ?)",
            (query, context_pack, trace),
        )
        self._maybe_commit()

    def get_retrieval_logs(self, limit: int = 20) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM retrieval_logs ORDER BY ts DESC LIMIT ?", (limit,)
        ).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["context_pack"] = json.loads(d["context_pack"])
            d["trace"] = json.loads(d["trace"])
            result.append(d)
        return result
