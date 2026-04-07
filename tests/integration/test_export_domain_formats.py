import asyncio

import pytest

from orenyl import server
from orenyl.context_pack import ContextPackBuilder
from orenyl.db import Database
from orenyl.lineage import LineageEngine
from orenyl.models import Event


def _reset_server(monkeypatch, db):
    monkeypatch.setattr(server, "db", db)
    monkeypatch.setattr(server, "engine", LineageEngine(db))
    monkeypatch.setattr(server, "pack_builder", ContextPackBuilder(db))


def test_export_domain_supports_json_markdown_timeline(monkeypatch):
    db = Database(":memory:")
    _reset_server(monkeypatch, db)
    ev = Event(
        id="event:test:health:export",
        type="diet_preference",
        payload={"value": "vegan"},
        domains=["health"],
        sensitivity="high",
    )
    db.insert_event(ev)
    server.engine.derive_facts_for_event(db.get_event(ev.id))

    out = asyncio.run(server.handle_export_domain({"domain": "health", "format": "markdown"}))
    assert "# Domain Export" in out[0].text


def test_export_domain_restricted_requires_scope_even_without_auth_fields(monkeypatch):
    db = Database(":memory:")
    _reset_server(monkeypatch, db)
    ev = Event(
        id="event:test:restricted:export",
        type="diet_preference",
        payload={"value": "vegan"},
        domains=["health"],
        sensitivity="restricted",
    )
    db.insert_event(ev)
    server.engine.derive_facts_for_event(db.get_event(ev.id))

    with pytest.raises(PermissionError, match="forbidden"):
        asyncio.run(server.handle_export_domain({"domain": "health", "format": "json"}))


def test_export_domain_does_not_apply_retrieval_consent_filtering(monkeypatch):
    # export_domain is an admin/DSAR surface; retrieval-consent scoping applies only to
    # retrieve_context, not to history/export paths. Events are returned regardless of
    # subject consent status or strict-mode setting.
    db = Database(":memory:")
    _reset_server(monkeypatch, db)
    ev = Event(
        id="event:test:export:no-strict",
        type="diet_preference",
        payload={"value": "vegan"},
        domains=["health"],
    )
    db.insert_event(ev)

    out = asyncio.run(server.handle_export_domain({"domain": "health", "format": "json"}))

    assert '"domain": "health"' in out[0].text
