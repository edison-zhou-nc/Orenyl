import asyncio
import json

import pytest

from lore import server
from lore.context_pack import ContextPackBuilder
from lore.db import Database
from lore.lineage import LineageEngine


def _reset_server(monkeypatch):
    fresh_db = Database(":memory:")
    monkeypatch.setattr(server, "db", fresh_db)
    monkeypatch.setattr(server, "engine", LineageEngine(fresh_db))
    monkeypatch.setattr(server, "pack_builder", ContextPackBuilder(fresh_db))


def test_store_event_rejects_unknown_sensitivity(monkeypatch):
    _reset_server(monkeypatch)

    out = asyncio.run(
        server.handle_store_event(
            {
                "domains": ["general"],
                "type": "note",
                "payload": {"text": "hello"},
                "sensitivity": "secret",
            }
        )
    )
    payload = json.loads(out[0].text)

    assert payload["stored"] is False
    assert payload["reason"] == "invalid_sensitivity"


def test_delete_and_recompute_rejects_unknown_target_type(monkeypatch):
    _reset_server(monkeypatch)

    with pytest.raises(ValueError, match="invalid_target_type"):
        asyncio.run(
            server.handle_delete_and_recompute(
                {
                    "target_id": "event:test",
                    "target_type": "mystery",
                }
            )
        )
