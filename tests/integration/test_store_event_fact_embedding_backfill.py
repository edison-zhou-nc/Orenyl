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


def test_store_event_backfills_derived_fact_embeddings(monkeypatch):
    db = Database(":memory:")
    _reset_server(monkeypatch, db)
    monkeypatch.setenv("LORE_EMBEDDING_PROVIDER", "hash-local")

    out = asyncio.run(
        server.handle_store_event(
            {
                "domains": ["health"],
                "type": "med_started",
                "payload": {"name": "metformin"},
            }
        )
    )
    payload = json.loads(out[0].text)
    fact_ids = payload["derived_facts"]
    assert fact_ids

    embeddings = db.get_fact_embeddings(fact_ids)
    assert embeddings
    for fact_id in fact_ids:
        assert fact_id in embeddings
