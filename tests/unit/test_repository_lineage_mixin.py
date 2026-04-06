from orenyl.db import Database
from orenyl.models import Edge, Event, Fact


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


def test_get_downstream_facts_is_bounded_to_100_recursive_hops():
    db = Database(":memory:")
    for i in range(150):
        db.insert_edge(
            Edge(
                parent_id=f"fact:test:{i}",
                parent_type="fact",
                child_id=f"fact:test:{i + 1}",
            )
        )

    result = db.get_downstream_facts("fact:test:0")

    assert len(result) == 100
    assert "fact:test:100" in result
    assert "fact:test:101" not in result
