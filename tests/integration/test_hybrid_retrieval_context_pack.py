from lore.context_pack import ContextPackBuilder
from lore.db import Database
from lore.lineage import LineageEngine
from lore.models import Event


def test_context_pack_uses_query_aware_hybrid_ranking():
    db = Database(":memory:")
    engine = LineageEngine(db)

    e1 = Event(id="event:test:med", type="med_started", payload={"name": "metformin"}, domains=["health"])
    e2 = Event(id="event:test:role", type="role_assigned", payload={"user": "u", "role": "admin"}, domains=["health"])
    db.insert_event(e1)
    db.insert_event(e2)
    engine.derive_facts_for_event(db.get_event(e1.id))
    engine.derive_facts_for_event(db.get_event(e2.id))

    pack = ContextPackBuilder(db).build(domain="health", query="metformin", limit=5)
    facts = pack.to_dict().get("facts", [])

    assert facts
    assert facts[0]["key"] == "active_medications"

