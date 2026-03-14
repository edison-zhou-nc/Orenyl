from __future__ import annotations

from lore.consent import ConsentService
from lore.context_pack import ContextPackBuilder
from lore.db import Database
from lore.lineage import LineageEngine
from lore.models import Event


def test_withdrawn_consent_excludes_subject_facts_from_retrieval(monkeypatch):
    monkeypatch.setenv("LORE_COMPLIANCE_STRICT_MODE", "1")

    db = Database(":memory:")
    engine = LineageEngine(db)
    builder = ContextPackBuilder(db)
    consent = ConsentService(db)

    ev = Event(
        id="event:test:consent-u123",
        type="med_started",
        payload={"name": "metformin"},
        domains=["health"],
        metadata={"subject_id": "user:123"},
    )
    db.insert_event(ev)
    engine.derive_facts_for_event(db.get_event(ev.id))

    before = builder.build(domain="health", query="med")
    assert len(before.facts) > 0

    consent.record(
        tenant_id="default",
        subject_id="user:123",
        purpose="retrieval",
        status="withdrawn",
        legal_basis="withdrawal",
    )
    after = builder.build(domain="health", query="med")
    assert len(after.facts) == 0
