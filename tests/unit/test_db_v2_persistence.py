import sqlite3
from pathlib import Path

import pytest

from lore.db import Database
from lore.models import Edge, Event, Fact


def _make_v1_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE events (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            payload TEXT NOT NULL,
            source TEXT DEFAULT 'user',
            ts TEXT NOT NULL,
            valid_from TEXT,
            valid_to TEXT,
            created_at TEXT NOT NULL,
            deleted_at TEXT
        );
        CREATE TABLE facts (
            id TEXT PRIMARY KEY,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            rule_id TEXT NOT NULL,
            valid_from TEXT NOT NULL,
            valid_to TEXT,
            created_at TEXT NOT NULL,
            invalidated_at TEXT,
            invalidation_reason TEXT
        );
        CREATE TABLE edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_id TEXT NOT NULL,
            parent_type TEXT NOT NULL,
            child_id TEXT NOT NULL,
            child_type TEXT NOT NULL DEFAULT 'fact',
            relation TEXT NOT NULL DEFAULT 'derived_from',
            created_at TEXT NOT NULL
        );
        CREATE TABLE tombstones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_id TEXT NOT NULL,
            target_type TEXT NOT NULL,
            reason TEXT,
            deleted_at TEXT NOT NULL,
            cascade_invalidated TEXT
        );
        CREATE TABLE retrieval_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT,
            context_pack TEXT NOT NULL,
            trace TEXT NOT NULL,
            ts TEXT NOT NULL
        );
        """
    )
    conn.commit()
    conn.close()


def _cols(conn, table):
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def test_migrate_v1_to_v2_adds_missing_columns(workspace_tmp_path):
    db_path = workspace_tmp_path / "v1.sqlite"
    _make_v1_db(db_path)

    db = Database(str(db_path))
    db.migrate_v1_to_v2()

    event_cols = _cols(db.conn, "events")
    assert {
        "content_hash",
        "sensitivity",
        "consent_source",
        "expires_at",
        "agent_id",
        "session_id",
    } <= event_cols

    fact_cols = _cols(db.conn, "facts")
    assert {"transform_config", "stale", "importance"} <= fact_cols


def test_insert_event_and_fact_persist_v2_fields_and_domains():
    db = Database(":memory:")

    ev = Event(
        id="event:test:v2",
        type="note",
        payload={"text": "hello"},
        domains=["health", "career"],
        content_hash="abc123",
        sensitivity="high",
        consent_source="explicit",
        expires_at="2030-01-01T00:00:00Z",
        metadata={"agent_id": "agent-1", "session_id": "session-1"},
    )
    db.insert_event(ev)

    row = db.conn.execute(
        "SELECT content_hash, sensitivity, consent_source, expires_at, agent_id, session_id FROM events WHERE id = ?",
        (ev.id,),
    ).fetchone()
    assert tuple(row) == (
        "abc123",
        "high",
        "explicit",
        "2030-01-01T00:00:00Z",
        "agent-1",
        "session-1",
    )

    domains = {
        r[0]
        for r in db.conn.execute(
            "SELECT domain FROM event_domains WHERE event_id = ?", (ev.id,)
        ).fetchall()
    }
    assert domains == {"health", "career"}

    fact = Fact(
        id="fact:test:v2",
        key="k",
        value={"x": 1},
        transform_config={"strategy": "simple"},
        stale=True,
        importance=0.8,
        rule_id="Rule@v1",
    )
    db.insert_fact(fact)

    frow = db.conn.execute(
        "SELECT transform_config, stale, importance FROM facts WHERE id = ?",
        (fact.id,),
    ).fetchone()
    assert frow[0] == '{"strategy": "simple"}'
    assert frow[1] == 1
    assert frow[2] == 0.8


def test_insert_event_respects_outer_transaction_rollback():
    db = Database(":memory:")
    event = Event(id="event:test:tx", type="note", payload={"text": "tx"})

    with pytest.raises(RuntimeError, match="rollback"):
        with db.transaction():
            db.insert_event(event)
            raise RuntimeError("rollback")

    assert db.get_event(event.id) is None


def test_insert_fact_respects_outer_transaction_rollback():
    db = Database(":memory:")
    fact = Fact(id="fact:test:tx", key="tx_key", value={"v": 1}, rule_id="Rule@tx")

    with pytest.raises(RuntimeError, match="rollback"):
        with db.transaction():
            db.insert_fact(fact)
            raise RuntimeError("rollback")

    assert db.get_fact(fact.id) is None


def test_insert_edge_respects_outer_transaction_rollback():
    db = Database(":memory:")
    edge = Edge(
        parent_id="event:test:parent",
        parent_type="event",
        child_id="fact:test:child",
        child_type="fact",
        relation="derived",
    )

    with pytest.raises(RuntimeError, match="rollback"):
        with db.transaction():
            db.insert_edge(edge)
            raise RuntimeError("rollback")

    assert db.get_parents(edge.child_id) == []


def test_insert_edge_rejects_duplicate_lineage_edge():
    db = Database(":memory:")
    edge = Edge(
        parent_id="event:test:parent",
        parent_type="event",
        child_id="fact:test:child",
        child_type="fact",
        relation="derived_from",
    )
    db.insert_edge(edge)

    with pytest.raises(sqlite3.IntegrityError):
        db.insert_edge(edge)


def test_batch_parent_and_event_fetch_helpers():
    db = Database(":memory:")
    event = Event(
        id="event:test:batch",
        type="note",
        payload={"text": "hello"},
        domains=["health"],
        sensitivity="high",
    )
    db.insert_event(event)
    fact = Fact(
        id="fact:test:batch",
        key="k",
        value={"v": 1},
        rule_id="Rule@batch",
    )
    db.insert_fact(fact)
    db.insert_edge(
        Edge(
            parent_id=event.id,
            parent_type="event",
            child_id=fact.id,
            child_type="fact",
            relation="derived_from",
        )
    )

    grouped = db.get_parents_for_children([fact.id])
    assert fact.id in grouped
    assert grouped[fact.id][0]["parent_id"] == event.id

    events = db.get_events_by_ids([event.id])
    assert event.id in events
    assert events[event.id]["domains"] == ["health"]
