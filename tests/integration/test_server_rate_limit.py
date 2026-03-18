import asyncio
import json

import pytest
from mcp.server.auth.provider import AccessToken

from lore import server
from lore.context_pack import ContextPackBuilder
from lore.db import Database
from lore.lineage import LineageEngine
from lore.rate_limit import RateLimiter


class _Verifier:
    async def verify_token(self, token: str):
        return AccessToken(
            token=token,
            client_id="tenant-a",
            scopes=["memory:read"],
            resource="tenant-a",
        )


def test_call_tool_enforces_per_tenant_rate_limit(monkeypatch):
    fresh_db = Database(":memory:")
    monkeypatch.setattr(server, "db", fresh_db)
    monkeypatch.setattr(server, "engine", LineageEngine(fresh_db))
    monkeypatch.setattr(server, "pack_builder", ContextPackBuilder(fresh_db))
    monkeypatch.setattr(server, "_get_token_verifier", lambda: _Verifier())
    monkeypatch.setattr(
        server,
        "_rate_limiter",
        RateLimiter(max_requests=1, window_seconds=60),
        raising=False,
    )

    first = asyncio.run(server.call_tool("list_events", {"_auth_token": "ok", "domain": "general"}))
    first_payload = json.loads(first[0].text)

    assert "events" in first_payload

    with pytest.raises(PermissionError, match="rate_limited"):
        asyncio.run(server.call_tool("list_events", {"_auth_token": "ok", "domain": "general"}))
