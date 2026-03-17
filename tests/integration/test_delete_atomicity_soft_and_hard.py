import pytest

from lore.db import Database
from lore.lineage import LineageEngine
from lore.models import Event


def test_soft_delete_rolls_back_on_stale_mark_failure(monkeypatch):
    db = Database(":memory:")
    engine = LineageEngine(db)
    ev = Event(id="event:test:soft", type="diet_preference", payload={"value": "vegan"})
    db.insert_event(ev)
    engine.derive_facts_for_event(db.get_event(ev.id))

    def boom(*_args, **_kwargs):
        raise RuntimeError("simulated_failure")

    monkeypatch.setattr(db, "mark_facts_stale", boom)

    with pytest.raises(RuntimeError, match="simulated_failure"):
        engine.delete_and_recompute(ev.id, "event", reason="test")

    assert db.get_event(ev.id) is not None
    assert db.get_tombstones(ev.id) == []
    facts_after = db.get_current_facts("diet_preference")
    assert len(facts_after) == 1
    assert facts_after[0]["value"].get("value") == "vegan"


def test_fact_delete_recompute_rolls_back_on_insert_failure(monkeypatch):
    db = Database(":memory:")
    engine = LineageEngine(db)
    ev = Event(
        id="event:test:fact-rollback", type="diet_preference", payload={"value": "vegetarian"}
    )
    db.insert_event(ev)
    derived_ids = engine.derive_facts_for_event(db.get_event(ev.id))
    fact_id = derived_ids[0]

    def boom(*_args, **_kwargs):
        raise RuntimeError("simulated_insert_failure")

    monkeypatch.setattr(db, "insert_fact", boom)

    with pytest.raises(RuntimeError, match="simulated_insert_failure"):
        engine.delete_and_recompute(fact_id, "fact", reason="test")

    fact_after = db.get_fact(fact_id)
    assert fact_after is not None
    assert fact_after["invalidated_at"] is None
    assert db.get_tombstones(fact_id) == []
