from __future__ import annotations

import asyncio
import json

from lore.consent import ConsentService
from lore.context_pack import ContextPackBuilder
from lore import server
from lore.db import Database
from lore.lineage import LineageEngine
from lore.models import Event


def _reset_server(monkeypatch, db: Database) -> None:
    monkeypatch.setattr(server, "db", db)
    monkeypatch.setattr(server, "engine", LineageEngine(db))
    monkeypatch.setattr(server, "pack_builder", ContextPackBuilder(db))


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


def test_withdrawn_consent_does_not_suppress_events_from_list_events(monkeypatch):
    # list_events is an admin/history surface; retrieval-consent filtering applies only
    # to retrieve_context. Withdrawn consent must not hide events from admin views.
    monkeypatch.setenv("LORE_COMPLIANCE_STRICT_MODE", "1")
    db = Database(":memory:")
    _reset_server(monkeypatch, db)
    consent = ConsentService(db)

    ev = Event(
        id="event:test:consent-list-u123",
        type="med_started",
        payload={"name": "metformin"},
        domains=["health"],
        metadata={"subject_id": "user:123"},
    )
    db.insert_event(ev)
    server.engine.derive_facts_for_event(db.get_event(ev.id))
    consent.record(
        tenant_id="default",
        subject_id="user:123",
        purpose="retrieval",
        status="withdrawn",
        legal_basis="withdrawal",
    )

    out = asyncio.run(server.handle_list_events({"domain": "health"}))
    payload = json.loads(out[0].text)

    assert payload["count"] == 1
    assert payload["events"][0]["id"] == "event:test:consent-list-u123"


def test_withdrawn_consent_does_not_suppress_events_from_export_domain(monkeypatch):
    # export_domain is an admin/DSAR surface; retrieval-consent filtering applies only
    # to retrieve_context. Withdrawn consent must not hide events from export views.
    monkeypatch.setenv("LORE_COMPLIANCE_STRICT_MODE", "1")
    db = Database(":memory:")
    _reset_server(monkeypatch, db)
    consent = ConsentService(db)

    ev = Event(
        id="event:test:consent-export-u123",
        type="med_started",
        payload={"name": "metformin"},
        domains=["health"],
        metadata={"subject_id": "user:123"},
    )
    db.insert_event(ev)
    server.engine.derive_facts_for_event(db.get_event(ev.id))
    consent.record(
        tenant_id="default",
        subject_id="user:123",
        purpose="retrieval",
        status="withdrawn",
        legal_basis="withdrawal",
    )

    out = asyncio.run(server.handle_export_domain({"domain": "health", "format": "json"}))
    payload = json.loads(out[0].text)

    assert len(payload["events"]) == 1
    assert payload["events"][0]["id"] == "event:test:consent-export-u123"
