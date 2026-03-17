import asyncio
import json

from lore import server
from lore.context_pack import ContextPackBuilder
from lore.db import Database
from lore.lineage import LineageEngine
from lore.models import Event


def _reset_server(monkeypatch, db):
    monkeypatch.setattr(server, "db", db)
    monkeypatch.setattr(server, "engine", LineageEngine(db))
    monkeypatch.setattr(server, "pack_builder", ContextPackBuilder(db))


def test_list_events_has_total_count(monkeypatch):
    db = Database(":memory:")
    _reset_server(monkeypatch, db)

    for i in range(3):
        ev = Event(
            id=f"event:test:list:{i}",
            type="note",
            payload={"text": f"event {i}"},
            domains=["general"],
        )
        db.insert_event(ev)

    out = asyncio.run(server.handle_list_events({"domain": "general", "limit": 2, "offset": 0}))
    data = json.loads(out[0].text)

    assert "total_count" in data
    assert data["total_count"] == 3
    assert data["count"] == 2
    assert len(data["events"]) == 2


def test_export_domain_json_has_events_facts_edges_summary(monkeypatch):
    db = Database(":memory:")
    _reset_server(monkeypatch, db)

    ev = Event(
        id="event:test:export:1",
        type="diet_preference",
        payload={"value": "omnivore"},
        domains=["preferences"],
    )
    db.insert_event(ev)
    server.engine.derive_facts_for_event(db.get_event(ev.id))

    out = asyncio.run(server.handle_export_domain({"domain": "preferences", "format": "json"}))
    data = json.loads(out[0].text)

    assert isinstance(data.get("events"), list)
    assert isinstance(data.get("facts"), list)
    assert isinstance(data.get("edges"), list)
    assert isinstance(data.get("summary"), str)
