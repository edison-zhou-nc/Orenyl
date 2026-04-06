from orenyl.db import Database
from orenyl.lineage import LineageEngine
from orenyl.models import Event


def test_single_event_can_produce_facts_in_multiple_domains():
    db = Database(":memory:")
    engine = LineageEngine(db)
    ev = Event(id="event:test:1", type="note", payload={"text": "quit job because stress"})
    ev.domains = ["career", "health"]
    db.insert_event(ev)
    created = engine.derive_facts_for_event(db.get_event(ev.id))
    assert isinstance(created, list)
    assert len(created) >= 1
    assert any(any(p["parent_id"] == ev.id for p in db.get_parents(fact_id)) for fact_id in created)
