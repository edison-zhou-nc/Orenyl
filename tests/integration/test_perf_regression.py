import asyncio
import json
import time

import pytest

from lore import server
from lore.context_pack import ContextPackBuilder
from lore.db import Database
from lore.lineage import LineageEngine


@pytest.mark.perf
def test_perf_regression_smoke(monkeypatch) -> None:
    db = Database(":memory:")
    monkeypatch.setattr(server, "db", db)
    monkeypatch.setattr(server, "engine", LineageEngine(db))
    monkeypatch.setattr(server, "pack_builder", ContextPackBuilder(db))
    server._reset_runtime_state_for_tests()

    started = time.perf_counter()
    store_payload = json.loads(
        asyncio.run(
            server.handle_store_event(
                {
                    "domains": ["general"],
                    "type": "note",
                    "payload": {"text": "perf smoke event"},
                }
            )
        )[0].text
    )
    asyncio.run(server.handle_retrieve_context_pack({"domain": "general", "query": "perf"}))
    delete_payload = json.loads(
        asyncio.run(
            server.handle_delete_and_recompute(
                {
                    "target_id": store_payload["event_id"],
                    "target_type": "event",
                    "mode": "soft",
                    "reason": "perf_smoke",
                }
            )
        )[0].text
    )
    elapsed = time.perf_counter() - started

    assert store_payload["stored"] is True
    assert delete_payload["checks"]["deletion_verified"] is True
    assert elapsed < 5.0
