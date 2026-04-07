import json

from orenyl.compliance import ComplianceService
from orenyl.context_pack import ContextPackBuilder
from orenyl.db import Database
from orenyl.lineage import LineageEngine
from orenyl.models import Event


def test_subject_erasure_purges_only_affected_tenant_retrieval_logs():
    db = Database(":memory:")
    engine = LineageEngine(db)
    builder = ContextPackBuilder(db)
    compliance = ComplianceService(db=db, engine=engine)

    event_a = Event(
        id="event:test:retrieval-log:a",
        type="med_started",
        payload={"name": "insulin"},
        domains=["health"],
        tenant_id="tenant-a",
        metadata={"subject_id": "subject-a"},
    )
    event_b = Event(
        id="event:test:retrieval-log:b",
        type="med_started",
        payload={"name": "metformin"},
        domains=["health"],
        tenant_id="tenant-b",
        metadata={"subject_id": "subject-b"},
    )
    db.insert_event(event_a)
    db.insert_event(event_b)
    engine.derive_facts_for_event(db.get_event(event_a.id, tenant_id="tenant-a"))
    engine.derive_facts_for_event(db.get_event(event_b.id, tenant_id="tenant-b"))

    builder.build(domain="health", query="insulin", tenant_id="tenant-a")
    builder.build(domain="health", query="metformin", tenant_id="tenant-b")

    before_a = db.get_retrieval_logs(limit=10, tenant_id="tenant-a")
    before_b = db.get_retrieval_logs(limit=10, tenant_id="tenant-b")
    assert before_a
    assert before_b

    compliance.erase_subject_data(subject_id="subject-a", mode="hard", tenant_id="tenant-a")

    after_a = db.get_retrieval_logs(limit=10, tenant_id="tenant-a")
    after_b = db.get_retrieval_logs(limit=10, tenant_id="tenant-b")

    assert after_a == []
    assert len(after_b) == 1
    assert json.dumps(after_b[0]["context_pack"]).lower().find("metformin") != -1


def test_soft_delete_preserves_retrieval_logs_for_recoverable_records():
    db = Database(":memory:")
    engine = LineageEngine(db)
    builder = ContextPackBuilder(db)

    event = Event(
        id="event:test:retrieval-soft",
        type="med_started",
        payload={"name": "insulin"},
        domains=["health"],
        tenant_id="tenant-a",
    )
    db.insert_event(event)
    engine.derive_facts_for_event(db.get_event(event.id, tenant_id="tenant-a"))
    builder.build(domain="health", query="insulin", tenant_id="tenant-a")

    before = db.get_retrieval_logs(limit=10, tenant_id="tenant-a")
    assert len(before) == 1

    engine.delete_and_recompute(
        target_id=event.id,
        target_type="event",
        reason="user_request",
        mode="soft",
        tenant_id="tenant-a",
    )

    after = db.get_retrieval_logs(limit=10, tenant_id="tenant-a")
    assert len(after) == 1
    assert json.dumps(after[0]["context_pack"]).lower().find("insulin") != -1


def test_hard_delete_purges_only_logs_referencing_deleted_lineage():
    db = Database(":memory:")
    engine = LineageEngine(db)

    health_event = Event(
        id="event:test:retrieval-hard-health",
        type="med_started",
        payload={"name": "insulin"},
        domains=["health"],
        tenant_id="tenant-a",
    )
    db.insert_event(health_event)
    engine.derive_facts_for_event(db.get_event(health_event.id, tenant_id="tenant-a"))
    downstream_ids = db.get_downstream_facts(health_event.id, tenant_id="tenant-a")
    assert downstream_ids

    db.log_retrieval(
        query="insulin",
        context_pack=json.dumps(
            {
                "items": [
                    {
                        "id": downstream_ids[0],
                        "provenance": {"derived_from": [health_event.id]},
                    }
                ]
            }
        ),
        trace=json.dumps([{"item_id": downstream_ids[0], "lineage": [health_event.id]}]),
        tenant_id="tenant-a",
    )
    db.log_retrieval(
        query="vegan",
        context_pack=json.dumps(
            {
                "items": [
                    {
                        "id": "fact:tenant-a:other:v1",
                        "provenance": {"derived_from": ["event:test:other-lineage"]},
                    }
                ]
            }
        ),
        trace=json.dumps(
            [{"item_id": "fact:tenant-a:other:v1", "lineage": ["event:test:other-lineage"]}]
        ),
        tenant_id="tenant-a",
    )
    db.log_retrieval(
        query="metformin",
        context_pack=json.dumps(
            {
                "items": [
                    {
                        "id": "fact:tenant-b:other:v1",
                        "provenance": {"derived_from": ["event:test:tenant-b"]},
                    }
                ]
            }
        ),
        trace=json.dumps(
            [{"item_id": "fact:tenant-b:other:v1", "lineage": ["event:test:tenant-b"]}]
        ),
        tenant_id="tenant-b",
    )

    before_a = db.get_retrieval_logs(limit=10, tenant_id="tenant-a")
    before_b = db.get_retrieval_logs(limit=10, tenant_id="tenant-b")
    assert len(before_a) == 2
    assert len(before_b) == 1

    engine.delete_and_recompute(
        target_id=health_event.id,
        target_type="event",
        reason="subject_erasure",
        mode="hard",
        tenant_id="tenant-a",
    )

    after_a = db.get_retrieval_logs(limit=10, tenant_id="tenant-a")
    after_b = db.get_retrieval_logs(limit=10, tenant_id="tenant-b")

    assert len(after_a) == 1
    assert after_a[0]["query"] == "vegan"
    assert len(after_b) == 1
    assert after_b[0]["query"] == "metformin"
