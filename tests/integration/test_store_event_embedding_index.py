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


def test_store_event_indexes_event_embedding(monkeypatch):
    db = Database(":memory:")
    _reset_server(monkeypatch, db)
    monkeypatch.setenv("LORE_EMBEDDING_PROVIDER", "hash-local")

    result = asyncio.run(server.handle_store_event({
        "domains": ["health"],
        "content": "I started metformin yesterday",
        "type": "note",
    }))
    payload = json.loads(result[0].text)
    event_id = payload["event_id"]

    embedding = db.get_event_embedding(event_id)
    assert embedding is not None
    assert embedding["model_id"] == "hash-local"
    assert embedding["vector"]
