from orenyl.db import Database
from orenyl.lineage import LineageEngine
from orenyl.models import Event


def test_same_rule_output_can_be_derived_in_multiple_tenants():
    db = Database(":memory:")
    engine = LineageEngine(db)

    tenant_a_event = Event(
        id="event:test:tenant-safe:a",
        type="med_started",
        payload={"name": "insulin"},
        domains=["health"],
        tenant_id="tenant-a",
    )
    tenant_b_event = Event(
        id="event:test:tenant-safe:b",
        type="med_started",
        payload={"name": "metformin"},
        domains=["health"],
        tenant_id="tenant-b",
    )

    db.insert_event(tenant_a_event)
    created_a = engine.derive_facts_for_event(db.get_event(tenant_a_event.id, tenant_id="tenant-a"))

    db.insert_event(tenant_b_event)
    created_b = engine.derive_facts_for_event(db.get_event(tenant_b_event.id, tenant_id="tenant-b"))

    tenant_a_facts = db.get_current_facts_by_domain("health", tenant_id="tenant-a")
    tenant_b_facts = db.get_current_facts_by_domain("health", tenant_id="tenant-b")

    assert created_a
    assert created_b
    assert {fact["tenant_id"] for fact in tenant_a_facts} == {"tenant-a"}
    assert {fact["tenant_id"] for fact in tenant_b_facts} == {"tenant-b"}
    assert {fact["id"] for fact in tenant_a_facts}.isdisjoint(
        {fact["id"] for fact in tenant_b_facts}
    )
