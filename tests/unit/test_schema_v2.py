from lore.db import Database


def _cols(conn, table):
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def test_schema_has_v2_tables_and_columns():
    db = Database(":memory:")
    conn = db.conn
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "event_domains" in tables
    assert "domain_registry" in tables
    assert "checkpoints" in tables

    event_cols = _cols(conn, "events")
    assert {"content_hash", "sensitivity", "consent_source", "expires_at", "agent_id", "session_id"} <= event_cols

    fact_cols = _cols(conn, "facts")
    assert {"transform_config", "stale", "importance"} <= fact_cols


def test_schema_has_v2_constraints_indexes_and_fk():
    db = Database(":memory:")
    conn = db.conn

    event_info = {row[1]: row for row in conn.execute("PRAGMA table_info(events)").fetchall()}
    assert event_info["sensitivity"][3] == 1
    assert event_info["consent_source"][3] == 1
    assert event_info["sensitivity"][4] == "'medium'"
    assert event_info["consent_source"][4] == "'implicit'"

    fact_info = {row[1]: row for row in conn.execute("PRAGMA table_info(facts)").fetchall()}
    assert fact_info["transform_config"][3] == 1
    assert fact_info["stale"][3] == 1
    assert fact_info["importance"][3] == 1
    assert fact_info["transform_config"][4] == "'{}'"
    assert fact_info["stale"][4] == "0"
    assert fact_info["importance"][4] == "0.5"

    fks = conn.execute("PRAGMA foreign_key_list(event_domains)").fetchall()
    assert any(row[2] == "events" and row[3] == "event_id" and row[4] == "id" for row in fks)

    indexes = {row[1] for row in conn.execute("PRAGMA index_list(events)").fetchall()}
    assert "idx_events_content_hash" in indexes
    assert "idx_events_agent_id" in indexes
    assert "idx_events_session_id" in indexes

    domain_indexes = {row[1] for row in conn.execute("PRAGMA index_list(event_domains)").fetchall()}
    assert "idx_event_domains_domain" in domain_indexes

    edge_indexes = {row[1] for row in conn.execute("PRAGMA index_list(edges)").fetchall()}
    assert "idx_edges_unique_relation" in edge_indexes

