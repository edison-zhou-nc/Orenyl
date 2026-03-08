import asyncio
import json

from lore import server
from lore.db import Database
from lore.models import Event


class _DummyPack:
    def to_json(self) -> str:
        return json.dumps({"ok": True})


class _DummyBuilder:
    def __init__(self):
        self.last_limit = None

    def build(self, **kwargs):
        self.last_limit = kwargs["limit"]
        return _DummyPack()


def test_list_events_clamps_limit_and_offset(monkeypatch):
    fresh_db = Database(":memory:")
    monkeypatch.setattr(server, "db", fresh_db)
    monkeypatch.setattr(server, "MAX_LIST_EVENTS_LIMIT", 2)

    for i in range(5):
        fresh_db.insert_event(Event(id=f"event:test:{i}", type="note", payload={"i": i}, domains=["general"]))

    out = asyncio.run(server.handle_list_events({"domain": "general", "limit": 50, "offset": -10}))
    payload = json.loads(out[0].text)

    assert payload["total_count"] == 5
    assert payload["count"] == 2
    assert len(payload["events"]) == 2


def test_retrieve_context_pack_clamps_limit(monkeypatch):
    dummy = _DummyBuilder()
    monkeypatch.setattr(server, "pack_builder", dummy)
    monkeypatch.setattr(server, "MAX_CONTEXT_PACK_LIMIT", 1)

    asyncio.run(server.handle_retrieve_context_pack({"domain": "general", "limit": 999}))

    assert dummy.last_limit == 1


def test_list_events_uses_db_pagination_path(monkeypatch):
    fresh_db = Database(":memory:")
    monkeypatch.setattr(server, "db", fresh_db)
    monkeypatch.setattr(server, "MAX_LIST_EVENTS_LIMIT", 2)

    for i in range(5):
        fresh_db.insert_event(Event(id=f"event:test:paged:{i}", type="note", payload={"i": i}, domains=["general"]))

    def fail_full_scan(*args, **kwargs):
        raise AssertionError("full_scan_not_allowed")

    monkeypatch.setattr(fresh_db, "get_all_events", fail_full_scan)
    monkeypatch.setattr(fresh_db, "get_active_events", fail_full_scan)

    out = asyncio.run(server.handle_list_events({"domain": "general", "limit": 50, "offset": 1}))
    payload = json.loads(out[0].text)

    assert payload["total_count"] == 5
    assert payload["count"] == 2
    assert len(payload["events"]) == 2

