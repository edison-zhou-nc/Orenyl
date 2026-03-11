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
    server._reset_runtime_state_for_tests()


def test_metrics_and_health_handlers(monkeypatch):
    db = Database(":memory:")
    _reset_server(monkeypatch, db)

    asyncio.run(server.handle_store_event({
        "domains": ["health"],
        "type": "med_started",
        "payload": {"name": "metformin"},
    }))
    asyncio.run(server.handle_retrieve_context_pack({"domain": "health", "query": "med"}))

    metrics_out = asyncio.run(server.handle_metrics({}))
    assert "lore_tool_calls_total" in metrics_out[0].text
    assert "lore_context_pack_latency_ms_count" in metrics_out[0].text

    health_out = asyncio.run(server.handle_health({}))
    health = json.loads(health_out[0].text)
    assert health["status"] == "ok"
    assert health["db_connected"] is True


def test_health_uses_database_ping(monkeypatch):
    class _Db:
        conn = None

        def ping(self):
            return True

    monkeypatch.setattr(server, "db", _Db())
    out = asyncio.run(server.handle_health({}))
    payload = json.loads(out[0].text)
    assert payload["db_connected"] is True
