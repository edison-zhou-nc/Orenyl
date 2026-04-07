import pytest

from orenyl.db import Database
from orenyl.models import Edge, Event, Fact


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


def test_fact_repository_requires_tenant_scope_for_unscoped_methods(monkeypatch):
    db = Database(":memory:")
    event = Event(
        id="event:test:repo-f2",
        type="note",
        payload={"text": "medication"},
        domains=["health"],
        tenant_id="tenant-a",
    )
    fact = Fact(
        id="fact:test:repo-f2",
        key="medication",
        value={"name": "metformin"},
        rule_id="MedicationRule",
        rule_version="v1",
        tenant_id="tenant-a",
    )

    db.insert_event(event)
    db.insert_fact(fact)
    db.insert_edge(
        Edge(parent_id=event.id, parent_type="event", child_id=fact.id, tenant_id="tenant-a")
    )
    monkeypatch.setenv("ORENYL_ENABLE_MULTI_TENANT", "1")

    with pytest.raises(PermissionError, match="tenant_scope_required"):
        db.list_current_facts_by_rule_family("MedicationRule", "v1")
    with pytest.raises(PermissionError, match="tenant_scope_required"):
        db.mark_facts_stale([fact.id])
    with pytest.raises(PermissionError, match="tenant_scope_required"):
        db.update_fact_rule_version(fact.id, "v2")

    assert db.list_current_facts_by_rule_family("MedicationRule", "v1", tenant_id="tenant-a")[0][
        "id"
    ] == fact.id
    assert db.mark_facts_stale([fact.id], tenant_id="tenant-a") == 1
    assert db.update_fact_rule_version(fact.id, "v2", tenant_id="tenant-a") is True
