import asyncio
import json

import pytest
from mcp.server.auth.provider import AccessToken

from lore import server
from lore.context_pack import ContextPackBuilder
from lore.db import Database
from lore.lineage import LineageEngine
from lore.models import Event


class _Verifier:
    async def verify_token(self, token: str):
        if token == "reader":
            return AccessToken(
                token=token,
                client_id="agent-a",
                scopes=["memory:read"],
                resource="tenant-a",
            )
        return None


def _reset(monkeypatch):
    fresh_db = Database(":memory:")
    monkeypatch.setattr(server, "db", fresh_db)
    monkeypatch.setattr(server, "engine", LineageEngine(fresh_db))
    monkeypatch.setattr(server, "pack_builder", ContextPackBuilder(fresh_db))
    monkeypatch.setattr(server, "_get_token_verifier", lambda: _Verifier())
    monkeypatch.setenv("LORE_ENABLE_MULTI_TENANT", "1")
    monkeypatch.setenv("LORE_ENABLE_AGENT_PERMISSIONS", "1")
    monkeypatch.setenv("LORE_POLICY_SHADOW_MODE", "0")
    event = Event(
        id="event:test:policy",
        type="med_started",
        payload={"name": "metformin"},
        domains=["health"],
        tenant_id="tenant-a",
    )
    fresh_db.insert_event(event)
    LineageEngine(fresh_db).derive_facts_for_event(fresh_db.get_event(event.id, tenant_id="tenant-a"))
    return fresh_db


def test_retrieve_context_pack_denied_without_permission(monkeypatch):
    _reset(monkeypatch)

    with pytest.raises(PermissionError, match="policy_denied"):
        asyncio.run(
            server.call_tool(
                "retrieve_context_pack",
                {"_auth_token": "reader", "domain": "health", "query": "meds"},
            )
        )


def test_retrieve_context_pack_allowed_with_permission(monkeypatch):
    db = _reset(monkeypatch)
    db.conn.execute(
        """INSERT INTO agent_permissions (tenant_id, agent_id, domain, action, effect)
           VALUES (?, ?, ?, ?, ?)""",
        ("tenant-a", "agent-a", "health", "read", "allow"),
    )
    db.conn.commit()

    out = asyncio.run(
        server.call_tool(
            "retrieve_context_pack",
            {"_auth_token": "reader", "domain": "health", "query": "meds"},
        )
    )
    payload = json.loads(out[0].text)
    assert payload["domain"] == "health"
