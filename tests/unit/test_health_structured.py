import asyncio
import json

from lore import server
from lore.context_pack import ContextPackBuilder
from lore.db import Database
from lore.lineage import LineageEngine


def test_health_payload_is_structured(monkeypatch) -> None:
    db = Database(":memory:")
    monkeypatch.setattr(server, "db", db)
    monkeypatch.setattr(server, "engine", LineageEngine(db))
    monkeypatch.setattr(server, "pack_builder", ContextPackBuilder(db))
    server._reset_runtime_state_for_tests()

    payload = json.loads(asyncio.run(server.handle_health({}))[0].text)

    assert {"status", "db_connected", "version", "transport"} <= set(payload)
    assert {"multi_tenant_enabled", "encryption_enabled"} <= set(payload)
