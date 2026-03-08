import asyncio
import json

from lore import server
from lore.context_pack import ContextPackBuilder
from lore.db import Database
from lore.lineage import LineageEngine


def _reset_server(monkeypatch, db):
    monkeypatch.setattr(server, "db", db)
    monkeypatch.setattr(server, "engine", LineageEngine(db))
    monkeypatch.setattr(server, "pack_builder", ContextPackBuilder(db))


def test_store_event_rejects_duplicate_hash_within_24h(monkeypatch):
    db = Database(":memory:")
    _reset_server(monkeypatch, db)

    first = asyncio.run(server.handle_store_event({
        "domains": ["health"],
        "content": "Started metformin",
        "type": "note",
    }))
    assert "event_id" in json.loads(first[0].text)

    second = asyncio.run(server.handle_store_event({
        "domains": ["health"],
        "content": " started   METFORMIN ",
        "type": "note",
    }))
    data = json.loads(second[0].text)
    assert data.get("duplicate") is True

