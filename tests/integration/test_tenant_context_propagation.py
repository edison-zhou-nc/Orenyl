import asyncio
import json

from mcp.server.auth.provider import AccessToken

from orenyl import server
from orenyl.context_pack import ContextPackBuilder
from orenyl.db import Database
from orenyl.lineage import LineageEngine
from orenyl.tenant import get_current_tenant_context


class _Verifier:
    async def verify_token(self, token: str):
        if token == "ok":
            return AccessToken(
                token=token,
                client_id="agent-1",
                scopes=["memory:read"],
                resource="tenant-a",
            )
        return None


def test_request_entrypoint_sets_and_clears_tenant_context(monkeypatch):
    monkeypatch.setenv("LORE_ENABLE_MULTI_TENANT", "1")
    fresh_db = Database(":memory:")
    monkeypatch.setattr(server, "db", fresh_db)
    monkeypatch.setattr(server, "engine", LineageEngine(fresh_db))
    monkeypatch.setattr(server, "pack_builder", ContextPackBuilder(fresh_db))
    monkeypatch.setattr(server, "_get_token_verifier", lambda: _Verifier())

    observed: dict[str, str | None] = {"during": None}

    async def _probe(args: dict):
        ctx = get_current_tenant_context()
        observed["during"] = ctx.tenant_id if ctx else None
        return [server.TextContent(type="text", text=json.dumps({"ok": True}))]

    monkeypatch.setattr(server, "handle_list_events", _probe)

    assert get_current_tenant_context() is None
    asyncio.run(server.call_tool("list_events", {"_auth_token": "ok", "domain": "general"}))
    assert observed["during"] == "tenant-a"
    assert get_current_tenant_context() is None
