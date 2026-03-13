import asyncio
import json

import pytest
from mcp.server.auth.provider import AccessToken

from lore import server
from lore.context_pack import ContextPackBuilder
from lore.db import Database
from lore.lineage import LineageEngine


class _TenantVerifier:
    async def verify_token(self, token: str):
        if token == "with-tenant":
            return AccessToken(
                token=token,
                client_id="user-1",
                scopes=["memory:read"],
                resource="tenant-a",
            )
        if token == "without-tenant":
            return AccessToken(
                token=token,
                client_id="user-2",
                scopes=["memory:read"],
                resource=None,
            )
        return None


def _reset(monkeypatch):
    fresh_db = Database(":memory:")
    monkeypatch.setattr(server, "db", fresh_db)
    monkeypatch.setattr(server, "engine", LineageEngine(fresh_db))
    monkeypatch.setattr(server, "pack_builder", ContextPackBuilder(fresh_db))
    monkeypatch.setattr(server, "_get_token_verifier", lambda: _TenantVerifier())


def test_request_without_tenant_claim_is_denied_when_multi_tenant_enabled(monkeypatch):
    _reset(monkeypatch)
    monkeypatch.setenv("LORE_ENABLE_MULTI_TENANT", "1")

    with pytest.raises(PermissionError, match="tenant_scope_violation"):
        asyncio.run(
            server.call_tool(
                "retrieve_context_pack",
                {"_auth_token": "without-tenant", "domain": "general", "query": ""},
            )
        )


def test_request_with_tenant_claim_succeeds_when_multi_tenant_enabled(monkeypatch):
    _reset(monkeypatch)
    monkeypatch.setenv("LORE_ENABLE_MULTI_TENANT", "1")

    out = asyncio.run(
        server.call_tool(
            "retrieve_context_pack",
            {"_auth_token": "with-tenant", "domain": "general", "query": ""},
        )
    )
    payload = json.loads(out[0].text)
    assert payload["domain"] == "general"


def test_default_tenant_used_when_multi_tenant_disabled(monkeypatch):
    _reset(monkeypatch)
    monkeypatch.setenv("LORE_ENABLE_MULTI_TENANT", "0")
    observed: dict[str, str] = {}

    async def _capture(args: dict):
        observed["tenant_id"] = args.get("_auth_tenant_id", "")
        return [server.TextContent(type="text", text=json.dumps({"ok": True}))]

    monkeypatch.setattr(server, "handle_list_events", _capture)

    asyncio.run(
        server.call_tool(
            "list_events",
            {"_auth_token": "without-tenant", "domain": "general"},
        )
    )

    assert observed["tenant_id"] == "default"
