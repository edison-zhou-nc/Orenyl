import sqlite3

from lore.db import Database
from lore.lineage import LineageEngine
from lore.models import Event


def test_facts_unique_key_version_index_exists():
    db = Database(":memory:")

    indexes = db.conn.execute("PRAGMA index_list(facts)").fetchall()
    unique_indexes = {row[1] for row in indexes if row[2] == 1}
    assert "idx_facts_key_version_unique" in unique_indexes

    index_cols = [
        row[2]
        for row in db.conn.execute("PRAGMA index_info(idx_facts_key_version_unique)").fetchall()
    ]
    assert index_cols == ["key", "version"]


def test_concurrent_derivation_does_not_drop_fact_version(monkeypatch):
    db = Database(":memory:")
    engine = LineageEngine(db)
    ev = Event(id="event:test:race", type="diet_preference", payload={"value": "vegan"})
    db.insert_event(ev)

    original_insert_fact = db.insert_fact
    calls = {"n": 0}

    def conflict_then_compete(fact):
        calls["n"] += 1
        if calls["n"] == 1:
            # Simulate another writer winning this version first.
            original_insert_fact(fact)
            raise sqlite3.IntegrityError("UNIQUE constraint failed: facts.key, facts.version")
        return original_insert_fact(fact)

    monkeypatch.setattr(db, "insert_fact", conflict_then_compete)

    created_ids = engine.derive_facts_for_event(db.get_event(ev.id))

    assert "fact:diet_preference:v2" in created_ids
    versions = db.get_facts_by_key("diet_preference")
    assert [f["version"] for f in versions] == [1, 2]
    assert versions[0]["invalidated_at"] is not None
    assert versions[1]["invalidated_at"] is None
