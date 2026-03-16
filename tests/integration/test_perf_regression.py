import asyncio
import json
import time

import pytest
from mcp.server.auth.provider import AccessToken

from lore import server
from lore.context_pack import ContextPackBuilder
from lore.db import Database
from lore.lineage import LineageEngine


class _Verifier:
    async def verify_token(self, token: str):
        if token == "ok":
            return AccessToken(
                token=token,
                client_id="perf-agent",
                scopes=["memory:read", "memory:write", "memory:delete"],
                resource="default",
            )
        return None


@pytest.mark.perf
def test_perf_regression_smoke(monkeypatch) -> None:
    db = Database(":memory:")
    monkeypatch.setattr(server, "db", db)
    monkeypatch.setattr(server, "engine", LineageEngine(db))
    monkeypatch.setattr(server, "pack_builder", ContextPackBuilder(db))
    monkeypatch.setattr(server, "_get_token_verifier", lambda: _Verifier())
    server._reset_runtime_state_for_tests()

    started = time.perf_counter()
    for index in range(3):
        store_payload = json.loads(
            asyncio.run(
                server.call_tool(
                    "store_event",
                    {
                        "_auth_token": "ok",
                        "domains": ["general"],
                        "type": "note",
                        "payload": {"text": f"perf smoke event {index}"},
                    },
                )
            )[0].text
        )
        retrieve_payload = json.loads(
            asyncio.run(
                server.call_tool(
                    "retrieve_context_pack",
                    {"_auth_token": "ok", "domain": "general", "query": "perf smoke"},
                )
            )[0].text
        )
        delete_payload = json.loads(
            asyncio.run(
                server.call_tool(
                    "delete_and_recompute",
                    {
                        "_auth_token": "ok",
                        "target_id": store_payload["event_id"],
                        "target_type": "event",
                        "mode": "soft",
                        "reason": "perf_smoke",
                    },
                )
            )[0].text
        )

        assert store_payload["stored"] is True
        assert retrieve_payload["domain"] == "general"
        assert "facts" in retrieve_payload
        assert delete_payload["checks"]["deletion_verified"] is True

    elapsed = time.perf_counter() - started

    assert elapsed < 5.0
