from lore.db import Database
from lore.lineage import LineageEngine
from lore.models import Edge, Event, Fact


def test_delete_and_recompute_handles_recursive_downstream_chain():
    db = Database(":memory:")
    engine = LineageEngine(db)
    root = Event(id="event:test:root", type="note", payload={"text": "root"})
    db.insert_event(root)
    fact_ids = ["fact:test:1", "fact:test:2", "fact:test:3"]
    for index, fact_id in enumerate(fact_ids, start=1):
        db.insert_fact(
            Fact(
                id=fact_id,
                key=f"chain_{index}",
                value={"step": index},
                rule_id="Rule@v1",
            )
        )
    db.insert_edge(Edge(parent_id=root.id, parent_type="event", child_id="fact:test:1"))
    db.insert_edge(Edge(parent_id="fact:test:1", parent_type="fact", child_id="fact:test:2"))
    db.insert_edge(Edge(parent_id="fact:test:2", parent_type="fact", child_id="fact:test:3"))

    proof = engine.delete_and_recompute(root.id, "event", reason="recursive-cascade")

    assert db.get_downstream_facts(root.id) == fact_ids
    assert proof.invalidated_facts == fact_ids
    assert proof.checks["skip_count"] == 0
    assert proof.checks["stale_marked"] == 3
    assert proof.checks["deletion_verified"] is True
    assert proof.checks["resurfaced_references"] == []
    assert proof.checks["target_in_active_events"] is False


def test_get_downstream_facts_deduplicates_convergent_descendants():
    db = Database(":memory:")
    root = Event(id="event:test:fanout", type="note", payload={"text": "fanout"})
    db.insert_event(root)
    db.insert_fact(Fact(id="fact:test:left", key="left", value={"side": "left"}, rule_id="Rule@v1"))
    db.insert_fact(
        Fact(id="fact:test:right", key="right", value={"side": "right"}, rule_id="Rule@v1")
    )
    db.insert_fact(
        Fact(id="fact:test:shared", key="shared", value={"side": "shared"}, rule_id="Rule@v1")
    )
    db.insert_edge(Edge(parent_id=root.id, parent_type="event", child_id="fact:test:left"))
    db.insert_edge(Edge(parent_id=root.id, parent_type="event", child_id="fact:test:right"))
    db.insert_edge(
        Edge(parent_id="fact:test:left", parent_type="fact", child_id="fact:test:shared")
    )
    db.insert_edge(
        Edge(parent_id="fact:test:right", parent_type="fact", child_id="fact:test:shared")
    )

    assert db.get_downstream_facts(root.id) == [
        "fact:test:left",
        "fact:test:right",
        "fact:test:shared",
    ]


def test_recursive_downstream_is_tenant_scoped():
    db = Database(":memory:")
    for tenant in ("tenant-a", "tenant-b"):
        root = Event(
            id=f"event:{tenant}:root",
            type="note",
            payload={"tenant": tenant},
            tenant_id=tenant,
        )
        db.insert_event(root)
        db.insert_fact(
            Fact(
                id=f"fact:{tenant}:1",
                key="shared_key",
                value={"tenant": tenant, "step": 1},
                rule_id="Rule@v1",
                tenant_id=tenant,
            )
        )
        db.insert_fact(
            Fact(
                id=f"fact:{tenant}:2",
                key="shared_key_child",
                value={"tenant": tenant, "step": 2},
                rule_id="Rule@v1",
                tenant_id=tenant,
            )
        )
        db.insert_edge(
            Edge(
                parent_id=root.id,
                parent_type="event",
                child_id=f"fact:{tenant}:1",
                tenant_id=tenant,
            )
        )
        db.insert_edge(
            Edge(
                parent_id=f"fact:{tenant}:1",
                parent_type="fact",
                child_id=f"fact:{tenant}:2",
                tenant_id=tenant,
            )
        )

    assert db.get_downstream_facts("event:tenant-a:root", tenant_id="tenant-a") == [
        "fact:tenant-a:1",
        "fact:tenant-a:2",
    ]
    assert db.get_downstream_facts("event:tenant-b:root", tenant_id="tenant-b") == [
        "fact:tenant-b:1",
        "fact:tenant-b:2",
    ]
