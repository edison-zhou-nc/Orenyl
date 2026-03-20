import json

from lore.compliance import ComplianceService
from lore.context_pack import ContextPackBuilder
from lore.db import Database
from lore.lineage import LineageEngine
from lore.models import Event


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
