"""SQLite database layer for Lore governed memory."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .repositories.audit import AuditMixin
from .repositories.compliance import ComplianceMixin
from .repositories.embeddings import EmbeddingMixin
from .repositories.events import EventMixin
from .repositories.facts import FactMixin
from .repositories.federation import FederationMixin
from .repositories.lineage import LineageMixin

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


class Database(
    EventMixin,
    FactMixin,
    LineageMixin,
    ComplianceMixin,
    FederationMixin,
    EmbeddingMixin,
    AuditMixin,
):
    """Database shell that preserves the public API through mixin composition."""

    def __init__(self, db_path: str = ":memory:"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._in_transaction = False
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=5000")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()

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
        # Legacy artifact from early phase-4 draft; hash chain lives in audit DB.
        self.conn.execute("DROP TABLE IF EXISTS audit_hash_chain")
        # Ensure uniqueness is enforced for existing DBs upgraded prior to this index.
        self.conn.execute("DROP INDEX IF EXISTS idx_facts_key_version_unique")
        self.conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_facts_key_version_unique "
            "ON facts(tenant_id, key, version)"
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
            fact_cols = {row[1] for row in self.conn.execute("PRAGMA table_info(facts)").fetchall()}
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
                for row in self.conn.execute("PRAGMA table_info(event_embeddings)").fetchall()
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

        if "retrieval_logs" in tables:
            retrieval_cols = {
                row[1] for row in self.conn.execute("PRAGMA table_info(retrieval_logs)").fetchall()
            }
            if "tenant_id" not in retrieval_cols:
                _safe_add_column("ALTER TABLE retrieval_logs ADD COLUMN tenant_id TEXT")
            self.conn.execute(
                "UPDATE retrieval_logs SET tenant_id = 'default' WHERE tenant_id IS NULL"
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_retrieval_logs_tenant_ts "
                "ON retrieval_logs(tenant_id, ts)"
            )

        if "facts" in tables:
            self.conn.execute("DROP INDEX IF EXISTS idx_facts_key_version_unique")
            self.conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_facts_key_version_unique "
                "ON facts(tenant_id, key, version)"
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
