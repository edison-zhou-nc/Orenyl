"""SQLite database layer for Lore governed memory."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .embeddings import decode_vector, encode_vector
from .models import Event, Fact, Edge, Tombstone

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


class Database:
    def __init__(self, db_path: str = ":memory:"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._in_transaction = False
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=5000")
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
            if "retention_tier" not in event_cols:
                _safe_add_column(
                    "ALTER TABLE events ADD COLUMN retention_tier TEXT NOT NULL DEFAULT 'hot'"
                )
            if "archived_at" not in event_cols:
                _safe_add_column("ALTER TABLE events ADD COLUMN archived_at TEXT")
            if "agent_id" not in event_cols:
                _safe_add_column("ALTER TABLE events ADD COLUMN agent_id TEXT")
            if "session_id" not in event_cols:
                _safe_add_column("ALTER TABLE events ADD COLUMN session_id TEXT")
            if "tenant_id" not in event_cols:
                _safe_add_column("ALTER TABLE events ADD COLUMN tenant_id TEXT")
            self.conn.execute("UPDATE events SET tenant_id = 'default' WHERE tenant_id IS NULL")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_events_agent_id ON events(agent_id)")
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_session_id ON events(session_id)"
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_tenant_id ON events(tenant_id)"
            )

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
            if "confidence" not in fact_cols:
                _safe_add_column(
                    "ALTER TABLE facts ADD COLUMN confidence REAL NOT NULL DEFAULT 1.0"
                )
            if "model_id" not in fact_cols:
                _safe_add_column(
                    "ALTER TABLE facts ADD COLUMN model_id TEXT NOT NULL DEFAULT 'deterministic'"
                )
            if "rule_version" not in fact_cols:
                _safe_add_column(
                    "ALTER TABLE facts ADD COLUMN rule_version TEXT NOT NULL DEFAULT 'v1'"
                )
            if "tenant_id" not in fact_cols:
                _safe_add_column("ALTER TABLE facts ADD COLUMN tenant_id TEXT")
            self.conn.execute("UPDATE facts SET tenant_id = 'default' WHERE tenant_id IS NULL")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_tenant_id ON facts(tenant_id)")

        if "edges" in tables:
            edge_cols = {row[1] for row in self.conn.execute("PRAGMA table_info(edges)").fetchall()}
            if "tenant_id" not in edge_cols:
                _safe_add_column("ALTER TABLE edges ADD COLUMN tenant_id TEXT")
            self.conn.execute("UPDATE edges SET tenant_id = 'default' WHERE tenant_id IS NULL")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_tenant_id ON edges(tenant_id)")

        if "tombstones" in tables:
            tombstone_cols = {
                row[1] for row in self.conn.execute("PRAGMA table_info(tombstones)").fetchall()
            }
            if "tenant_id" not in tombstone_cols:
                _safe_add_column("ALTER TABLE tombstones ADD COLUMN tenant_id TEXT")
            self.conn.execute("UPDATE tombstones SET tenant_id = 'default' WHERE tenant_id IS NULL")
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_tombstones_tenant_id ON tombstones(tenant_id)"
            )

        if "event_embeddings" in tables:
            event_embedding_cols = {
                row[1]
                for row in self.conn.execute(
                    "PRAGMA table_info(event_embeddings)"
                ).fetchall()
            }
            if "tenant_id" not in event_embedding_cols:
                _safe_add_column("ALTER TABLE event_embeddings ADD COLUMN tenant_id TEXT")
            self.conn.execute(
                "UPDATE event_embeddings SET tenant_id = 'default' WHERE tenant_id IS NULL"
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_event_embeddings_tenant_id "
                "ON event_embeddings(tenant_id)"
            )

        if "fact_embeddings" in tables:
            fact_embedding_cols = {
                row[1] for row in self.conn.execute("PRAGMA table_info(fact_embeddings)").fetchall()
            }
            if "tenant_id" not in fact_embedding_cols:
                _safe_add_column("ALTER TABLE fact_embeddings ADD COLUMN tenant_id TEXT")
            self.conn.execute(
                "UPDATE fact_embeddings SET tenant_id = 'default' WHERE tenant_id IS NULL"
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_fact_embeddings_tenant_id "
                "ON fact_embeddings(tenant_id)"
            )

        self.conn.commit()

    def close(self):
        self.conn.close()

    def ping(self) -> bool:
        try:
            self.conn.execute("SELECT 1").fetchone()
            return True
        except Exception:
            return False

    # ── Events ──────────────────────────────────────────────

    def insert_event(self, event: Event) -> str:
        self.conn.execute(
            """INSERT INTO events (
                   id, type, payload, content_hash, sensitivity, consent_source,
                   expires_at, metadata, retention_tier, archived_at, agent_id,
                   session_id, source, tenant_id, ts, valid_from, valid_to, created_at
               )
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event.id,
                event.type,
                json.dumps(event.payload),
                event.content_hash,
                event.sensitivity,
                event.consent_source,
                event.expires_at,
                json.dumps(event.metadata),
                event.metadata.get("retention_tier", "hot"),
                event.metadata.get("archived_at"),
                event.metadata.get("agent_id"),
                event.metadata.get("session_id"),
                event.source,
                event.tenant_id or event.metadata.get("tenant_id", "default"),
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

    def get_event(self, event_id: str, tenant_id: str = "") -> dict | None:
        row = self.conn.execute(
            """SELECT * FROM events
               WHERE id = ?
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (event_id, tenant_id, tenant_id),
        ).fetchone()
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
            "SELECT id FROM events WHERE content_hash = ? "
            "AND deleted_at IS NULL ORDER BY ts DESC LIMIT 1",
            (content_hash,),
        ).fetchone()
        if row is None:
            return None
        return self.get_event(row["id"])

    def get_active_events(self, event_type: str | None = None, tenant_id: str = "") -> list[dict]:
        if event_type:
            rows = self.conn.execute(
                """SELECT * FROM events
                   WHERE deleted_at IS NULL
                     AND type = ?
                     AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)
                   ORDER BY ts""",
                (event_type, tenant_id, tenant_id),
            ).fetchall()
        else:
            rows = self.conn.execute(
                """SELECT * FROM events
                   WHERE deleted_at IS NULL
                     AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)
                   ORDER BY ts""",
                (tenant_id, tenant_id),
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

    def get_recent_events_in_domains(
        self,
        domains: list[str],
        since_ts: str,
        tenant_id: str = "",
    ) -> list[dict]:
        if not domains:
            return []
        domains_json = json.dumps(domains)
        rows = self.conn.execute(
            """SELECT DISTINCT e.*
               FROM events e
               JOIN event_domains ed ON ed.event_id = e.id
               WHERE e.deleted_at IS NULL
                 AND e.ts >= ?
                 AND (NULLIF(?, '') IS NULL OR COALESCE(e.tenant_id, 'default') = ?)
                 AND ed.domain IN (SELECT value FROM json_each(?))
               ORDER BY e.ts DESC""",
            (since_ts, tenant_id, tenant_id, domains_json),
        ).fetchall()
        result: list[dict] = []
        for row in rows:
            data = dict(row)
            data["payload"] = json.loads(data["payload"])
            data["metadata"] = json.loads(data["metadata"])
            data["domains"] = [
                r[0]
                for r in self.conn.execute(
                    "SELECT domain FROM event_domains WHERE event_id = ? ORDER BY domain",
                    (data["id"],),
                ).fetchall()
            ]
            result.append(data)
        return result

    def get_facts_by_ids(self, fact_ids: list[str], tenant_id: str = "") -> list[dict]:
        if not fact_ids:
            return []
        fact_ids_json = json.dumps(fact_ids)
        rows = self.conn.execute(
            """SELECT * FROM facts
               WHERE id IN (SELECT value FROM json_each(?))
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (fact_ids_json, tenant_id, tenant_id),
        ).fetchall()
        out: list[dict] = []
        for row in rows:
            data = dict(row)
            data["value"] = json.loads(data["value"])
            data["transform_config"] = json.loads(data["transform_config"])
            data["stale"] = bool(data["stale"])
            out.append(data)
        return out

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

    def get_active_events_by_domains(self, domains: list[str], tenant_id: str = "") -> list[dict]:
        normalized = [d.strip().lower() for d in domains if d and d.strip()]
        if not normalized:
            return self.get_active_events(tenant_id=tenant_id)
        domains_json = json.dumps(normalized)
        rows = self.conn.execute(
            """SELECT DISTINCT e.*
                FROM events e
                JOIN event_domains ed ON ed.event_id = e.id
                WHERE e.deleted_at IS NULL
                  AND (NULLIF(?, '') IS NULL OR COALESCE(e.tenant_id, 'default') = ?)
                  AND ed.domain IN (SELECT value FROM json_each(?))
                ORDER BY e.ts""",
            (tenant_id, tenant_id, domains_json),
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

    def get_events_by_domains(
        self,
        domains: list[str],
        include_tombstoned: bool = False,
        tenant_id: str = "",
    ) -> list[dict]:
        normalized = [d.strip().lower() for d in domains if d and d.strip()]
        if not normalized:
            if include_tombstoned:
                rows = self.conn.execute(
                    """SELECT e.*
                       FROM events e
                       WHERE (NULLIF(?, '') IS NULL OR COALESCE(e.tenant_id, 'default') = ?)
                       ORDER BY e.ts""",
                    (tenant_id, tenant_id),
                ).fetchall()
            else:
                rows = self.conn.execute(
                    """SELECT e.*
                       FROM events e
                       WHERE e.deleted_at IS NULL
                         AND (NULLIF(?, '') IS NULL OR COALESCE(e.tenant_id, 'default') = ?)
                       ORDER BY e.ts""",
                    (tenant_id, tenant_id),
                ).fetchall()
        else:
            domains_json = json.dumps(normalized)
            if include_tombstoned:
                rows = self.conn.execute(
                    """SELECT DISTINCT e.*
                        FROM events e
                        JOIN event_domains ed ON ed.event_id = e.id
                        WHERE ed.domain IN (SELECT value FROM json_each(?))
                          AND (NULLIF(?, '') IS NULL OR COALESCE(e.tenant_id, 'default') = ?)
                        ORDER BY e.ts""",
                    (domains_json, tenant_id, tenant_id),
                ).fetchall()
            else:
                rows = self.conn.execute(
                    """SELECT DISTINCT e.*
                        FROM events e
                        JOIN event_domains ed ON ed.event_id = e.id
                        WHERE ed.domain IN (SELECT value FROM json_each(?))
                          AND e.deleted_at IS NULL
                          AND (NULLIF(?, '') IS NULL OR COALESCE(e.tenant_id, 'default') = ?)
                        ORDER BY e.ts""",
                    (domains_json, tenant_id, tenant_id),
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

    def count_events_by_domains(
        self,
        domains: list[str],
        include_tombstoned: bool = False,
        tenant_id: str = "",
    ) -> int:
        normalized = [d.strip().lower() for d in domains if d and d.strip()]
        if not normalized:
            if include_tombstoned:
                row = self.conn.execute(
                    """SELECT COUNT(*)
                       FROM events
                       WHERE (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
                    (tenant_id, tenant_id),
                ).fetchone()
            else:
                row = self.conn.execute(
                    """SELECT COUNT(*)
                       FROM events
                       WHERE deleted_at IS NULL
                         AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
                    (tenant_id, tenant_id),
                ).fetchone()
            return int(row[0] or 0)

        domains_json = json.dumps(normalized)
        if include_tombstoned:
            row = self.conn.execute(
                """SELECT COUNT(DISTINCT e.id)
                   FROM events e
                   JOIN event_domains ed ON ed.event_id = e.id
                   WHERE ed.domain IN (SELECT value FROM json_each(?))
                     AND (NULLIF(?, '') IS NULL OR COALESCE(e.tenant_id, 'default') = ?)""",
                (domains_json, tenant_id, tenant_id),
            ).fetchone()
        else:
            row = self.conn.execute(
                """SELECT COUNT(DISTINCT e.id)
                   FROM events e
                   JOIN event_domains ed ON ed.event_id = e.id
                   WHERE ed.domain IN (SELECT value FROM json_each(?))
                     AND e.deleted_at IS NULL
                     AND (NULLIF(?, '') IS NULL OR COALESCE(e.tenant_id, 'default') = ?)""",
                (domains_json, tenant_id, tenant_id),
            ).fetchone()
        return int(row[0] or 0)

    def list_events_page(
        self,
        domains: list[str],
        include_tombstoned: bool,
        limit: int,
        offset: int,
        tenant_id: str = "",
    ) -> list[dict]:
        safe_limit = max(1, int(limit))
        safe_offset = max(0, int(offset))
        normalized = [d.strip().lower() for d in domains if d and d.strip()]

        if not normalized:
            if include_tombstoned:
                rows = self.conn.execute(
                    """SELECT e.*
                        FROM events e
                        WHERE (NULLIF(?, '') IS NULL OR COALESCE(e.tenant_id, 'default') = ?)
                        ORDER BY e.ts
                        LIMIT ? OFFSET ?""",
                    (tenant_id, tenant_id, safe_limit, safe_offset),
                ).fetchall()
            else:
                rows = self.conn.execute(
                    """SELECT e.*
                        FROM events e
                        WHERE e.deleted_at IS NULL
                          AND (NULLIF(?, '') IS NULL OR COALESCE(e.tenant_id, 'default') = ?)
                        ORDER BY e.ts
                        LIMIT ? OFFSET ?""",
                    (tenant_id, tenant_id, safe_limit, safe_offset),
                ).fetchall()
        else:
            domains_json = json.dumps(normalized)
            if include_tombstoned:
                rows = self.conn.execute(
                    """SELECT DISTINCT e.*
                        FROM events e
                        JOIN event_domains ed ON ed.event_id = e.id
                        WHERE ed.domain IN (SELECT value FROM json_each(?))
                          AND (NULLIF(?, '') IS NULL OR COALESCE(e.tenant_id, 'default') = ?)
                        ORDER BY e.ts
                        LIMIT ? OFFSET ?""",
                    (domains_json, tenant_id, tenant_id, safe_limit, safe_offset),
                ).fetchall()
            else:
                rows = self.conn.execute(
                    """SELECT DISTINCT e.*
                        FROM events e
                        JOIN event_domains ed ON ed.event_id = e.id
                        WHERE ed.domain IN (SELECT value FROM json_each(?))
                          AND e.deleted_at IS NULL
                          AND (NULLIF(?, '') IS NULL OR COALESCE(e.tenant_id, 'default') = ?)
                        ORDER BY e.ts
                        LIMIT ? OFFSET ?""",
                    (domains_json, tenant_id, tenant_id, safe_limit, safe_offset),
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

    def get_event_count(self, domain: str = "general", tenant_id: str = "") -> int:
        if domain and domain != "general":
            row = self.conn.execute(
                """SELECT COUNT(DISTINCT e.id)
                   FROM events e
                   JOIN event_domains ed ON ed.event_id = e.id
                   WHERE e.deleted_at IS NULL
                     AND ed.domain = ?
                     AND (NULLIF(?, '') IS NULL OR COALESCE(e.tenant_id, 'default') = ?)""",
                (domain, tenant_id, tenant_id),
            ).fetchone()
            return int(row[0] or 0)
        row = self.conn.execute(
            """SELECT COUNT(*) FROM events
               WHERE deleted_at IS NULL
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (tenant_id, tenant_id),
        ).fetchone()
        return int(row[0] or 0)

    def get_latest_event_ts(self, domain: str = "general", tenant_id: str = "") -> str | None:
        if domain and domain != "general":
            row = self.conn.execute(
                """SELECT MAX(e.ts)
                   FROM events e
                   JOIN event_domains ed ON ed.event_id = e.id
                   WHERE e.deleted_at IS NULL
                     AND ed.domain = ?
                     AND (NULLIF(?, '') IS NULL OR COALESCE(e.tenant_id, 'default') = ?)""",
                (domain, tenant_id, tenant_id),
            ).fetchone()
            return row[0]
        row = self.conn.execute(
            """SELECT MAX(ts) FROM events
               WHERE deleted_at IS NULL
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (tenant_id, tenant_id),
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

    def soft_delete_event(self, event_id: str, deleted_at: str, tenant_id: str = "") -> bool:
        cur = self.conn.execute(
            """UPDATE events
               SET deleted_at = ?
               WHERE id = ?
                 AND deleted_at IS NULL
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (deleted_at, event_id, tenant_id, tenant_id),
        )
        self._maybe_commit()
        return cur.rowcount > 0

    def hard_delete_event(self, event_id: str, tenant_id: str = "") -> bool:
        self.conn.execute(
            """DELETE FROM event_domains
               WHERE event_id IN (
                   SELECT id FROM events
                   WHERE id = ?
                     AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)
               )""",
            (event_id, tenant_id, tenant_id),
        )
        cur = self.conn.execute(
            """DELETE FROM events
               WHERE id = ?
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (event_id, tenant_id, tenant_id),
        )
        self._maybe_commit()
        return cur.rowcount > 0

    def update_event_payload(self, event_id: str, payload: dict[str, Any]) -> bool:
        cur = self.conn.execute(
            "UPDATE events SET payload = ? WHERE id = ?",
            (json.dumps(payload), event_id),
        )
        self._maybe_commit()
        return cur.rowcount > 0

    def update_event_retention(self, event_id: str, tier: str, archived_at: str | None) -> bool:
        cur = self.conn.execute(
            "UPDATE events SET retention_tier = ?, archived_at = ? WHERE id = ?",
            (tier, archived_at, event_id),
        )
        self._maybe_commit()
        return cur.rowcount > 0

    # ── Facts ───────────────────────────────────────────────

    def insert_fact(self, fact: Fact) -> str:
        self.conn.execute(
            """INSERT INTO facts (
                   id, key, value, transform_config, stale, importance,
                   version, rule_id, rule_version, confidence, model_id,
                   tenant_id, valid_from, valid_to, created_at
               )
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                fact.id,
                fact.key,
                json.dumps(fact.value),
                json.dumps(fact.transform_config),
                int(fact.stale),
                fact.importance,
                fact.version,
                fact.rule_id,
                fact.rule_version,
                fact.confidence,
                fact.model_id,
                fact.tenant_id,
                fact.valid_from,
                fact.valid_to,
                fact.created_at,
            ),
        )
        self._maybe_commit()
        return fact.id

    def get_current_facts(self, key: str | None = None, tenant_id: str = "") -> list[dict]:
        """Get all valid, non-invalidated facts (optionally filtered by key)."""
        if key:
            rows = self.conn.execute(
                """SELECT * FROM facts
                   WHERE invalidated_at IS NULL
                     AND key = ?
                     AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)
                   ORDER BY version DESC""",
                (key, tenant_id, tenant_id),
            ).fetchall()
        else:
            rows = self.conn.execute(
                """SELECT * FROM facts
                   WHERE invalidated_at IS NULL
                     AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)
                   ORDER BY key, version DESC""",
                (tenant_id, tenant_id),
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
        tenant_id: str = "",
        agent_id: str = "",
        session_id: str = "",
    ) -> list[dict]:
        if domain and domain != "general":
            rows = self.conn.execute(
                """SELECT DISTINCT f.*
                   FROM facts f
                   WHERE f.invalidated_at IS NULL
                     AND (NULLIF(?, '') IS NULL OR COALESCE(f.tenant_id, 'default') = ?)
                     AND EXISTS (
                         SELECT 1
                         FROM edges e
                         JOIN event_domains ed ON ed.event_id = e.parent_id
                         JOIN events ev ON ev.id = e.parent_id
                         WHERE e.child_id = f.id
                           AND e.parent_type = 'event'
                           AND ed.domain = ?
                           AND ev.archived_at IS NULL
                           AND (NULLIF(?, '') IS NULL OR COALESCE(ev.tenant_id, 'default') = ?)
                     )
                     AND NOT EXISTS (
                         SELECT 1
                         FROM edges e2
                         JOIN events ev2 ON ev2.id = e2.parent_id
                         WHERE e2.child_id = f.id
                           AND e2.parent_type = 'event'
                           AND (NULLIF(?, '') IS NULL OR COALESCE(ev2.tenant_id, 'default') = ?)
                           AND (
                               (NULLIF(?, '') IS NOT NULL AND COALESCE(ev2.agent_id, '') <> ?)
                               OR (NULLIF(?, '') IS NOT NULL AND COALESCE(ev2.session_id, '') <> ?)
                           )
                     )
                   ORDER BY f.key, f.version DESC""",
                (
                    tenant_id, tenant_id,
                    domain,
                    tenant_id, tenant_id,
                    tenant_id, tenant_id,
                    agent_id, agent_id,
                    session_id, session_id,
                ),
            ).fetchall()
        else:
            rows = self.conn.execute(
                """SELECT DISTINCT f.*
                   FROM facts f
                   WHERE f.invalidated_at IS NULL
                     AND (NULLIF(?, '') IS NULL OR COALESCE(f.tenant_id, 'default') = ?)
                     AND EXISTS (
                         SELECT 1
                         FROM edges e
                         JOIN events ev ON ev.id = e.parent_id
                         WHERE e.child_id = f.id
                           AND e.parent_type = 'event'
                           AND ev.archived_at IS NULL
                           AND (NULLIF(?, '') IS NULL OR COALESCE(ev.tenant_id, 'default') = ?)
                     )
                     AND NOT EXISTS (
                         SELECT 1
                         FROM edges e2
                         JOIN events ev2 ON ev2.id = e2.parent_id
                         WHERE e2.child_id = f.id
                           AND e2.parent_type = 'event'
                           AND (NULLIF(?, '') IS NULL OR COALESCE(ev2.tenant_id, 'default') = ?)
                           AND (
                               (NULLIF(?, '') IS NOT NULL AND COALESCE(ev2.agent_id, '') <> ?)
                               OR (NULLIF(?, '') IS NOT NULL AND COALESCE(ev2.session_id, '') <> ?)
                           )
                     )
                   ORDER BY f.key, f.version DESC""",
                (
                    tenant_id, tenant_id,
                    tenant_id, tenant_id,
                    tenant_id, tenant_id,
                    agent_id, agent_id,
                    session_id, session_id,
                ),
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

    def get_fact(self, fact_id: str, tenant_id: str = "") -> dict | None:
        row = self.conn.execute(
            """SELECT * FROM facts
               WHERE id = ?
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (fact_id, tenant_id, tenant_id),
        ).fetchone()
        if row is None:
            return None
        d = dict(row)
        d["value"] = json.loads(d["value"])
        d["transform_config"] = json.loads(d["transform_config"])
        d["stale"] = bool(d["stale"])
        return d

    def get_latest_version(self, key: str, tenant_id: str = "") -> int:
        row = self.conn.execute(
            """SELECT MAX(version) as max_v FROM facts
               WHERE key = ?
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (key, tenant_id, tenant_id),
        ).fetchone()
        return row["max_v"] or 0

    def invalidate_fact(
        self,
        fact_id: str,
        reason: str,
        invalidated_at: str,
        tenant_id: str = "",
    ) -> bool:
        cur = self.conn.execute(
            """UPDATE facts SET invalidated_at = ?, invalidation_reason = ?
               WHERE id = ?
                 AND invalidated_at IS NULL
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (invalidated_at, reason, fact_id, tenant_id, tenant_id),
        )
        self._maybe_commit()
        return cur.rowcount > 0

    def get_facts_by_key(self, key: str, tenant_id: str = "") -> list[dict]:
        """Get all versions of facts for a key (including invalidated)."""
        rows = self.conn.execute(
            """SELECT * FROM facts
               WHERE key = ?
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)
               ORDER BY version""",
            (key, tenant_id, tenant_id),
        ).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["value"] = json.loads(d["value"])
            d["transform_config"] = json.loads(d["transform_config"])
            d["stale"] = bool(d["stale"])
            result.append(d)
        return result

    def list_current_facts_by_rule_family(self, rule_family: str, version: str) -> list[dict]:
        rows = self.conn.execute(
            """SELECT * FROM facts
               WHERE invalidated_at IS NULL
                 AND rule_id = ?
                 AND rule_version = ?""",
            (rule_family, version),
        ).fetchall()
        result: list[dict] = []
        for row in rows:
            data = dict(row)
            data["value"] = json.loads(data["value"])
            data["transform_config"] = json.loads(data["transform_config"])
            data["stale"] = bool(data["stale"])
            result.append(data)
        return result

    def update_fact_rule_version(self, fact_id: str, to_version: str) -> bool:
        cur = self.conn.execute(
            "UPDATE facts SET rule_version = ? WHERE id = ?",
            (to_version, fact_id),
        )
        self._maybe_commit()
        return cur.rowcount > 0

    def register_rule_version(self, rule_family: str, version: str, active: bool) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO rule_registry (rule_family, version, active, created_at)
               VALUES (?, ?, ?, (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')))""",
            (rule_family, version, 1 if active else 0),
        )
        self._maybe_commit()

    def set_rule_version_active(self, rule_family: str, version: str, active: bool) -> None:
        self.conn.execute(
            "UPDATE rule_registry SET active = ? WHERE rule_family = ? AND version = ?",
            (1 if active else 0, rule_family, version),
        )
        self._maybe_commit()

    def get_active_rule_versions(self, rule_family: str) -> list[str]:
        rows = self.conn.execute(
            "SELECT version FROM rule_registry WHERE rule_family = ? AND active = 1",
            (rule_family,),
        ).fetchall()
        return [str(row["version"]) for row in rows]

    def has_agent_permission(
        self,
        tenant_id: str,
        agent_id: str,
        domain: str,
        action: str,
        at_ts: str,
    ) -> bool:
        row = self.conn.execute(
            """SELECT 1
               FROM agent_permissions
               WHERE tenant_id = ?
                 AND agent_id = ?
                 AND action = ?
                 AND effect = 'allow'
                 AND (domain = ? OR domain = '*')
                 AND (expires_at IS NULL OR expires_at > ?)
               LIMIT 1""",
            (tenant_id, agent_id, action, domain, at_ts),
        ).fetchone()
        return row is not None

    # ── Edges ───────────────────────────────────────────────

    def insert_edge(self, edge: Edge):
        self.conn.execute(
            """INSERT INTO edges (tenant_id, parent_id, parent_type, child_id, child_type, relation)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                edge.tenant_id,
                edge.parent_id,
                edge.parent_type,
                edge.child_id,
                edge.child_type,
                edge.relation,
            ),
        )
        self._maybe_commit()

    def get_children(self, parent_id: str, tenant_id: str = "") -> list[dict]:
        rows = self.conn.execute(
            """SELECT * FROM edges
               WHERE parent_id = ?
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (parent_id, tenant_id, tenant_id),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_parents(self, child_id: str, tenant_id: str = "") -> list[dict]:
        rows = self.conn.execute(
            """SELECT * FROM edges
               WHERE child_id = ?
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (child_id, tenant_id, tenant_id),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_parents_for_children(
        self,
        child_ids: list[str],
        tenant_id: str = "",
    ) -> dict[str, list[dict]]:
        if not child_ids:
            return {}
        child_ids_json = json.dumps(child_ids)
        rows = self.conn.execute(
            """SELECT * FROM edges
               WHERE child_id IN (SELECT value FROM json_each(?))
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (child_ids_json, tenant_id, tenant_id),
        ).fetchall()
        grouped: dict[str, list[dict]] = {child_id: [] for child_id in child_ids}
        for row in rows:
            edge = dict(row)
            grouped.setdefault(edge["child_id"], []).append(edge)
        return grouped

    def get_events_by_ids(self, event_ids: list[str], tenant_id: str = "") -> dict[str, dict]:
        if not event_ids:
            return {}
        event_ids_json = json.dumps(event_ids)
        rows = self.conn.execute(
            """SELECT * FROM events
               WHERE id IN (SELECT value FROM json_each(?))
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (event_ids_json, tenant_id, tenant_id),
        ).fetchall()
        domain_rows = self.conn.execute(
            (
                "SELECT event_id, domain FROM event_domains "
                "WHERE event_id IN (SELECT value FROM json_each(?)) ORDER BY domain"
            ),
            (event_ids_json,),
        ).fetchall()
        domains_by_event: dict[str, list[str]] = {event_id: [] for event_id in event_ids}
        for row in domain_rows:
            domains_by_event.setdefault(row["event_id"], []).append(row["domain"])

        events: dict[str, dict] = {}
        for row in rows:
            event = dict(row)
            event["payload"] = json.loads(event["payload"])
            event["metadata"] = json.loads(event["metadata"])
            event["domains"] = domains_by_event.get(event["id"], [])
            events[event["id"]] = event
        return events

    def get_downstream_facts(self, item_id: str, tenant_id: str = "") -> list[str]:
        """Recursively find downstream facts using a single SQL CTE."""
        rows = self.conn.execute(
            """
            WITH RECURSIVE graph(child_id) AS (
                SELECT child_id FROM edges
                WHERE parent_id = ?
                  AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)
                UNION
                SELECT e.child_id
                FROM edges e
                JOIN graph g ON e.parent_id = g.child_id
                WHERE (NULLIF(?, '') IS NULL OR COALESCE(e.tenant_id, 'default') = ?)
            )
            SELECT DISTINCT child_id FROM graph ORDER BY child_id
            """,
            (item_id, tenant_id, tenant_id, tenant_id, tenant_id),
        ).fetchall()
        return [str(row["child_id"]) for row in rows]

    def delete_edges_for_item(self, item_id: str, tenant_id: str = "") -> int:
        cur = self.conn.execute(
            """DELETE FROM edges
               WHERE (parent_id = ? OR child_id = ?)
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (item_id, item_id, tenant_id, tenant_id),
        )
        self._maybe_commit()
        return cur.rowcount

    def hard_delete_facts_by_source(self, event_id: str, tenant_id: str = "") -> int:
        rows = self.conn.execute(
            """SELECT child_id
               FROM edges
               WHERE parent_id = ?
                 AND parent_type = 'event'
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (event_id, tenant_id, tenant_id),
        ).fetchall()
        fact_ids = [row[0] for row in rows]
        deleted = 0
        for fact_id in fact_ids:
            self.delete_edges_for_item(fact_id, tenant_id=tenant_id)
            cur = self.conn.execute(
                """DELETE FROM facts
                   WHERE id = ?
                     AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
                (fact_id, tenant_id, tenant_id),
            )
            deleted += cur.rowcount
        self._maybe_commit()
        return deleted

    def mark_facts_stale(self, fact_ids: list[str]) -> int:
        if not fact_ids:
            return 0
        fact_ids_json = json.dumps(fact_ids)
        cur = self.conn.execute(
            "UPDATE facts SET stale = 1 WHERE id IN (SELECT value FROM json_each(?))",
            (fact_ids_json,),
        )
        self._maybe_commit()
        return cur.rowcount

    def run_vacuum(self) -> None:
        self.conn.execute("VACUUM")

    # ── Embeddings ───────────────────────────────────────────────

    def upsert_event_embedding(
        self,
        event_id: str,
        vector: list[float],
        model_id: str,
        tenant_id: str = "default",
    ) -> None:
        self.conn.execute(
            """INSERT INTO event_embeddings (event_id, tenant_id, model_id, vector)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(event_id) DO UPDATE SET
                 tenant_id = excluded.tenant_id,
                 model_id = excluded.model_id,
                 vector = excluded.vector,
                 created_at = (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))""",
            (event_id, tenant_id or "default", model_id, encode_vector(vector)),
        )
        self._maybe_commit()

    def get_event_embedding(self, event_id: str, tenant_id: str = "") -> dict | None:
        row = self.conn.execute(
            """SELECT event_id, tenant_id, model_id, vector, created_at
               FROM event_embeddings
               WHERE event_id = ?
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (event_id, tenant_id, tenant_id),
        ).fetchone()
        if row is None:
            return None
        data = dict(row)
        data["vector"] = decode_vector(data["vector"])
        return data

    def upsert_fact_embedding(
        self,
        fact_id: str,
        vector: list[float],
        model_id: str,
        tenant_id: str = "default",
    ) -> None:
        self.conn.execute(
            """INSERT INTO fact_embeddings (fact_id, tenant_id, model_id, vector)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(fact_id) DO UPDATE SET
                 tenant_id = excluded.tenant_id,
                 model_id = excluded.model_id,
                 vector = excluded.vector,
                 created_at = (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))""",
            (fact_id, tenant_id or "default", model_id, encode_vector(vector)),
        )
        self._maybe_commit()

    def get_fact_embeddings(self, fact_ids: list[str], tenant_id: str = "") -> dict[str, dict]:
        if not fact_ids:
            return {}
        fact_ids_json = json.dumps(fact_ids)
        rows = self.conn.execute(
            """SELECT fact_id, tenant_id, model_id, vector, created_at
               FROM fact_embeddings
               WHERE fact_id IN (SELECT value FROM json_each(?))
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (fact_ids_json, tenant_id, tenant_id),
        ).fetchall()
        result: dict[str, dict] = {}
        for row in rows:
            data = dict(row)
            data["vector"] = decode_vector(data["vector"])
            result[data["fact_id"]] = data
        return result

    # ── Tombstones ──────────────────────────────────────────

    def insert_tombstone(self, tombstone: Tombstone):
        self.conn.execute(
            """INSERT INTO tombstones (
                   tenant_id, target_id, target_type, reason, deleted_at, cascade_invalidated
               )
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                tombstone.tenant_id,
                tombstone.target_id,
                tombstone.target_type,
                tombstone.reason,
                tombstone.deleted_at, json.dumps(tombstone.cascade_invalidated),
            ),
        )
        self._maybe_commit()

    def get_tombstones(self, target_id: str | None = None, tenant_id: str = "") -> list[dict]:
        if target_id:
            rows = self.conn.execute(
                """SELECT * FROM tombstones
                   WHERE target_id = ?
                     AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
                (target_id, tenant_id, tenant_id),
            ).fetchall()
        else:
            rows = self.conn.execute(
                """SELECT * FROM tombstones
                   WHERE (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
                (tenant_id, tenant_id),
            ).fetchall()
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
