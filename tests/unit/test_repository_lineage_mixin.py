from lore.db import Database
from lore.models import Edge, Event, Fact


def test_lineage_repository_tracks_parent_child_relationships():
    db = Database(":memory:")
    event = Event(
        id="event:test:repo-l1",
        type="note",
        payload={"text": "seed"},
        domains=["general"],
    )
    fact = Fact(id="fact:test:repo-l1", key="topic", value="seed", rule_id="TopicRule@v1")

    db.insert_event(event)
    db.insert_fact(fact)
    db.insert_edge(Edge(parent_id=event.id, parent_type="event", child_id=fact.id))

    assert db.get_children(event.id)[0]["child_id"] == fact.id
    assert db.get_parents(fact.id)[0]["parent_id"] == event.id
    assert db.get_parents_for_children([fact.id])[fact.id][0]["parent_id"] == event.id
    assert db.get_downstream_facts(event.id) == [fact.id]
