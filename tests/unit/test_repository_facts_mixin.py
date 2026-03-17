from lore.db import Database
from lore.models import Edge, Event, Fact


def test_fact_repository_returns_latest_domain_facts_and_stale_state():
    db = Database(":memory:")
    event = Event(
        id="event:test:repo-f1",
        type="note",
        payload={"text": "medication"},
        domains=["health"],
    )
    fact = Fact(
        id="fact:test:repo-f1",
        key="medication",
        value={"name": "metformin"},
        rule_id="MedicationRule@v1",
    )

    db.insert_event(event)
    db.insert_fact(fact)
    db.insert_edge(Edge(parent_id=event.id, parent_type="event", child_id=fact.id))

    current = db.get_current_facts_by_domain("health")
    assert [item["id"] for item in current] == [fact.id]

    assert db.mark_facts_stale([fact.id]) == 1
    assert db.get_facts_by_ids([fact.id])[0]["stale"] is True
    assert db.get_facts_by_key("medication")[0]["value"] == {"name": "metformin"}
