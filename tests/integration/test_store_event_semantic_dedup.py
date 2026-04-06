import asyncio
import json

from orenyl import runtime
from orenyl import server
from orenyl.context_pack import ContextPackBuilder
from orenyl.db import Database
from orenyl.lazy import Lazy
from orenyl.lineage import LineageEngine


def _reset_server(monkeypatch, db):
    monkeypatch.setattr(server, "db", db)
    monkeypatch.setattr(server, "engine", LineageEngine(db))
    monkeypatch.setattr(server, "pack_builder", ContextPackBuilder(db))


class _FakeProvider:
    provider_id = "test-fake"

    def embed_text(self, text: str) -> list[float]:
        value = (text or "").lower()
        if "metformin" in value:
            return [1.0, 0.0]
        if "medication" in value:
            return [0.99, 0.01]
        return [0.0, 1.0]


def test_store_event_rejects_semantic_duplicate_when_enabled(monkeypatch):
    db = Database(":memory:")
    _reset_server(monkeypatch, db)
    monkeypatch.setenv("ORENYL_ENABLE_SEMANTIC_DEDUP", "1")
    monkeypatch.setenv("ORENYL_SEMANTIC_DEDUP_THRESHOLD_DEFAULT", "0.95")
    monkeypatch.setattr(runtime, "_embedding_provider_lazy", Lazy(lambda: _FakeProvider()))

    first = asyncio.run(
        server.handle_store_event(
            {
                "domains": ["health"],
                "content": "I started metformin",
                "type": "note",
            }
        )
    )
    assert "event_id" in json.loads(first[0].text)

    second = asyncio.run(
        server.handle_store_event(
            {
                "domains": ["health"],
                "content": "Began taking the medication",
                "type": "note",
            }
        )
    )
    data = json.loads(second[0].text)

    assert data.get("stored") is False
    assert data.get("duplicate") is True
    assert data.get("reason") == "semantic_duplicate_within_24h"
