import asyncio
import pytest
from lore import server
from lore.context_pack import ContextPackBuilder
from lore.db import Database
from lore.lineage import LineageEngine
from lore.models import Event


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
