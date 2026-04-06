import pytest

from orenyl.db import Database
from orenyl.lineage import LineageEngine
from orenyl.models import Event


def test_hard_delete_rolls_back_on_failure(monkeypatch):
    db = Database(":memory:")
    engine = LineageEngine(db)
    ev = Event(id="event:test:atomic", type="diet_preference", payload={"value": "vegan"})
    db.insert_event(ev)
    engine.derive_facts_for_event(db.get_event(ev.id))
    facts_before = db.get_current_facts("diet_preference")
    assert len(facts_before) == 1

    original = db.hard_delete_event

    def boom(event_id: str, tenant_id: str = ""):
        raise RuntimeError("simulated_failure")

    monkeypatch.setattr(db, "hard_delete_event", boom)

    with pytest.raises(RuntimeError, match="simulated_failure"):
        engine.delete_and_recompute(ev.id, "event", reason="gdpr", mode="hard")

    monkeypatch.setattr(db, "hard_delete_event", original)

    assert db.get_event(ev.id) is not None
    assert db.get_tombstones(ev.id) == []
    facts_after = db.get_current_facts("diet_preference")
    assert len(facts_after) == 1
    assert facts_after[0]["value"].get("value") == "vegan"
