import asyncio

import pytest
from mcp.server.auth.provider import AccessToken

from lore import audit
from lore import server
from lore.context_pack import ContextPackBuilder
from lore.db import Database
from lore.lineage import LineageEngine
from lore.models import Event


class StubVerifier:
    async def verify_token(self, token: str):
        if token == "read":
            return AccessToken(token=token, client_id="u1", scopes=["memory:read"])
        if token == "export":
            return AccessToken(token=token, client_id="u1", scopes=["memory:export"])
        if token == "admin":
            return AccessToken(
                token=token,
                client_id="u1",
                scopes=["memory:read", "memory:write", "memory:delete", "memory:export", "memory:export:restricted"],
            )
        return None


def _reset_server_state(monkeypatch):
    fresh_db = Database(":memory:")
    monkeypatch.setattr(server, "db", fresh_db)
    monkeypatch.setattr(server, "engine", LineageEngine(fresh_db))
    monkeypatch.setattr(server, "pack_builder", ContextPackBuilder(fresh_db))
    monkeypatch.setattr(server, "_token_verifier", StubVerifier())


def test_call_tool_denies_when_no_token(monkeypatch):
    _reset_server_state(monkeypatch)
    audit.clear_events()

    with pytest.raises(PermissionError, match="unauthorized"):
        asyncio.run(server.call_tool("list_events", {}))

    assert any(e["result"] == "deny" and e["action"] == "list_events" for e in audit.get_events())


def test_delete_and_recompute_requires_delete_scope(monkeypatch):
    _reset_server_state(monkeypatch)

    with pytest.raises(PermissionError, match="forbidden"):
        asyncio.run(
            server.call_tool(
                "delete_and_recompute",
                {"target_id": "event:test", "target_type": "event", "_auth_token": "read"},
            )
        )


def test_export_domain_restricted_requires_stronger_scope(monkeypatch):
    _reset_server_state(monkeypatch)

    ev = Event(
        id="event:test:restricted",
        type="diet_preference",
        payload={"value": "vegan"},
        domains=["health"],
        sensitivity="restricted",
    )
    server.db.insert_event(ev)
    server.engine.derive_facts_for_event(server.db.get_event(ev.id))

    with pytest.raises(PermissionError, match="forbidden"):
        asyncio.run(
            server.call_tool(
                "export_domain",
                {"domain": "health", "format": "json", "confirm_restricted": True, "_auth_token": "export"},
            )
        )
