import asyncio
import json

import pytest
from mcp.server.auth.provider import AccessToken

from orenyl import server
from orenyl.context_pack import ContextPackBuilder
from orenyl.db import Database
from orenyl.lineage import LineageEngine
from orenyl.models import Event


class _Verifier:
    async def verify_token(self, token: str):
        if token == "delegatee":
            return AccessToken(
                token=token,
                client_id="agent-b",
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
    monkeypatch.setenv("ORENYL_ENABLE_MULTI_TENANT", "1")
    monkeypatch.setenv("ORENYL_ENABLE_AGENT_PERMISSIONS", "1")
    monkeypatch.setenv("ORENYL_POLICY_SHADOW_MODE", "0")
    event = Event(
        id="event:test:delegation",
        type="med_started",
        payload={"name": "metformin"},
        domains=["health"],
        tenant_id="tenant-a",
    )
    fresh_db.insert_event(event)
    LineageEngine(fresh_db).derive_facts_for_event(
        fresh_db.get_event(event.id, tenant_id="tenant-a")
    )
    return fresh_db


def test_retrieve_context_pack_allowed_with_active_delegation(monkeypatch):
    db = _reset(monkeypatch)
    db.conn.execute(
        """INSERT INTO delegation_grants (
               tenant_id, grantor_agent_id, grantee_agent_id, domain, action, expires_at
           ) VALUES (?, ?, ?, ?, ?, ?)""",
        ("tenant-a", "agent-owner", "agent-b", "health", "read", "2099-01-01T00:00:00Z"),
    )
    db.conn.commit()

    out = asyncio.run(
        server.call_tool(
            "retrieve_context_pack",
            {"_auth_token": "delegatee", "domain": "health", "query": "meds"},
        )
    )
    payload = json.loads(out[0].text)
    assert payload["domain"] == "health"


def test_retrieve_context_pack_denied_when_delegation_expired(monkeypatch):
    db = _reset(monkeypatch)
    db.conn.execute(
        """INSERT INTO delegation_grants (
               tenant_id, grantor_agent_id, grantee_agent_id, domain, action, expires_at
           ) VALUES (?, ?, ?, ?, ?, ?)""",
        ("tenant-a", "agent-owner", "agent-b", "health", "read", "2026-03-11T23:59:59Z"),
    )
    db.conn.commit()

    with pytest.raises(PermissionError, match="policy_denied"):
        asyncio.run(
            server.call_tool(
                "retrieve_context_pack",
                {"_auth_token": "delegatee", "domain": "health", "query": "meds"},
            )
        )
