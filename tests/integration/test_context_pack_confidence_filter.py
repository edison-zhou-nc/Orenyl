from lore.context_pack import ContextPackBuilder
from lore.db import Database
from lore.models import Edge, Event, Fact


def test_context_pack_excludes_low_confidence_facts_by_default():
    db = Database(":memory:")
    event = Event(
        id="event:test:confidence",
        type="note",
        payload={"text": "seed"},
        domains=["health"],
    )
    db.insert_event(event)

    high = Fact(
        id="fact:high",
        key="high_conf",
        value={"v": 1},
        rule_id="Rule@high",
        confidence=0.92,
        model_id="llm-a",
    )
    low = Fact(
        id="fact:low",
        key="low_conf",
        value={"v": 2},
        rule_id="Rule@low",
        confidence=0.45,
        model_id="llm-a",
    )
    db.insert_fact(high)
    db.insert_fact(low)
    db.insert_edge(Edge(parent_id=event.id, parent_type="event", child_id=high.id))
    db.insert_edge(Edge(parent_id=event.id, parent_type="event", child_id=low.id))

    pack = ContextPackBuilder(db).build(domain="health", query="seed", limit=10)
    ids = {item["id"] for item in pack.items}
    assert "fact:high" in ids
    assert "fact:low" not in ids
