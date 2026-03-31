import asyncio
import json

from lore import runtime
from lore import server
from lore.context_pack import ContextPackBuilder
from lore.db import Database
from lore.lazy import Lazy
from lore.lineage import LineageEngine
from lore.models import Edge, Event, Fact


def _reset_server(monkeypatch, db):
    monkeypatch.setattr(server, "db", db)
    monkeypatch.setattr(server, "engine", LineageEngine(db))
    monkeypatch.setattr(server, "pack_builder", ContextPackBuilder(db))


class _FailingProvider:
    provider_id = "failing"

    def embed_text(self, text: str) -> list[float]:
        raise RuntimeError("upstream_unavailable")


def test_store_event_survives_embedding_provider_failure(monkeypatch):
    db = Database(":memory:")
    _reset_server(monkeypatch, db)
    monkeypatch.setattr(runtime, "_embedding_provider_lazy", Lazy(lambda: _FailingProvider()))

    result = asyncio.run(
        server.handle_store_event(
            {
                "domains": ["health"],
                "content": "Started metformin",
                "type": "note",
            }
        )
    )
    payload = json.loads(result[0].text)

    assert payload["stored"] is True
    assert payload["event_id"]


def test_context_pack_survives_vector_provider_failure(monkeypatch, caplog):
    db = Database(":memory:")
    event = Event(
        id="event:test:vector-fail",
        type="note",
        payload={"text": "seed"},
        domains=["health"],
    )
    db.insert_event(event)
    fact = Fact(
        id="fact:test:vector-fail",
        key="seed",
        value={"v": 1},
        rule_id="Rule@v1",
        confidence=1.0,
    )
    db.insert_fact(fact)
    db.insert_edge(Edge(parent_id=event.id, parent_type="event", child_id=fact.id))

    monkeypatch.setattr(
        runtime, "_embedding_provider_lazy", Lazy(lambda: _FailingProvider())
    )
    pack = ContextPackBuilder(db).build(domain="health", query="seed", limit=5)
    assert pack.items
    assert "embedding_pipeline_fallback" in caplog.text
