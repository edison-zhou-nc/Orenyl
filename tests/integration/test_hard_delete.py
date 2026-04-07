from orenyl.db import Database
from orenyl.lineage import LineageEngine
from orenyl.models import Event


def test_hard_delete_physically_removes_event():
    db = Database(":memory:")
    engine = LineageEngine(db)
    ev = Event(id="event:test:hd1", type="diet_preference", payload={"value": "vegan"})
    db.insert_event(ev)
    proof = engine.delete_and_recompute(ev.id, "event", reason="gdpr", mode="hard")
    assert proof.to_dict()["checks"]["deletion_verified"] is True
    assert db.get_event(ev.id) is None
