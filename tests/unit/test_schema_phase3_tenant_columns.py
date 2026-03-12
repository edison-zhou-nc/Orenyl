from lore.db import Database


def _cols(conn, table):
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def test_phase3_schema_has_tenant_id_columns():
    db = Database(":memory:")
    conn = db.conn

    assert "tenant_id" in _cols(conn, "events")
    assert "tenant_id" in _cols(conn, "facts")
    assert "tenant_id" in _cols(conn, "edges")
    assert "tenant_id" in _cols(conn, "tombstones")
    assert "tenant_id" in _cols(conn, "event_embeddings")
    assert "tenant_id" in _cols(conn, "fact_embeddings")


def test_phase3_schema_has_tenant_indexes_and_tables():
    db = Database(":memory:")
    conn = db.conn
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}

    assert "tenant_registry" in tables
    assert "agent_permissions" in tables
    assert "delegation_grants" in tables
    assert "sync_journal" in tables

    event_indexes = {r[1] for r in conn.execute("PRAGMA index_list(events)").fetchall()}
    fact_indexes = {r[1] for r in conn.execute("PRAGMA index_list(facts)").fetchall()}
    tombstone_indexes = {r[1] for r in conn.execute("PRAGMA index_list(tombstones)").fetchall()}

    assert "idx_events_tenant_id" in event_indexes
    assert "idx_facts_tenant_id" in fact_indexes
    assert "idx_tombstones_tenant_id" in tombstone_indexes
