import asyncio
import json

import pytest
from mcp.server.auth.provider import AccessToken

from orenyl import server
from orenyl.context_pack import ContextPackBuilder
from orenyl.db import Database
from orenyl.lineage import LineageEngine
from orenyl.models import Edge, Event, Fact


class _Verifier:
    async def verify_token(self, token: str):
        if token == "tenant-b-agent":
            return AccessToken(
                token=token,
                client_id="agent-b",
                scopes=[
                    "memory:read",
                    "memory:write",
                    "memory:delete",
                    "memory:export",
                ],
                resource="tenant-b",
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

    fresh_db.conn.execute(
        """INSERT INTO agent_permissions (tenant_id, agent_id, domain, action, effect)
           VALUES (?, ?, ?, ?, ?)""",
        ("tenant-b", "agent-b", "*", "read", "allow"),
    )
    fresh_db.conn.execute(
        """INSERT INTO agent_permissions (tenant_id, agent_id, domain, action, effect)
           VALUES (?, ?, ?, ?, ?)""",
        ("tenant-b", "agent-b", "*", "write", "allow"),
    )
    fresh_db.conn.commit()

    tenant_a_event = Event(
        id="event:tenant-a:health",
        type="med_started",
        payload={"name": "insulin"},
        domains=["health"],
        tenant_id="tenant-a",
    )
    tenant_b_event = Event(
        id="event:tenant-b:health",
        type="med_started",
        payload={"name": "metformin"},
        domains=["health"],
        tenant_id="tenant-b",
    )
    fresh_db.insert_event(tenant_a_event)
    fresh_db.insert_event(tenant_b_event)
    LineageEngine(fresh_db).derive_facts_for_event(
        fresh_db.get_event(tenant_a_event.id, tenant_id="tenant-a")
    )
    tenant_b_fact = Fact(
        id="fact:tenant-b:med",
        key="tenant_b_medication",
        value={"name": "metformin"},
        tenant_id="tenant-b",
    )
    fresh_db.insert_fact(tenant_b_fact)
    fresh_db.insert_edge(
        Edge(
            parent_id=tenant_b_event.id,
            parent_type="event",
            child_id=tenant_b_fact.id,
            tenant_id="tenant-b",
        )
    )
    return fresh_db


def test_all_tools_reject_cross_tenant_access(monkeypatch):
    db = _reset(monkeypatch)
    fact_id = db.get_current_facts_by_domain("health", tenant_id="tenant-a")[0]["id"]
    shared_args = {"_auth_token": "tenant-b-agent", "tenant_id": "tenant-a"}

    with pytest.raises(PermissionError, match="tenant_scope_violation"):
        asyncio.run(
            server.call_tool(
                "store_event",
                {
                    **shared_args,
                    "domains": ["health"],
                    "type": "note",
                    "payload": {"text": "cross-tenant write attempt"},
                },
            )
        )
    with pytest.raises(PermissionError, match="tenant_scope_violation"):
        asyncio.run(
            server.call_tool(
                "retrieve_context_pack",
                {**shared_args, "domain": "health", "query": "meds"},
            )
        )
    with pytest.raises(PermissionError, match="tenant_scope_violation"):
        asyncio.run(
            server.call_tool(
                "delete_and_recompute",
                {
                    **shared_args,
                    "target_id": "event:tenant-a:health",
                    "target_type": "event",
                },
            )
        )
    with pytest.raises(PermissionError, match="tenant_scope_violation"):
        asyncio.run(
            server.call_tool(
                "export_domain",
                {**shared_args, "domain": "health", "format": "json"},
            )
        )
    with pytest.raises(PermissionError, match="tenant_scope_violation"):
        asyncio.run(
            server.call_tool(
                "list_events",
                {**shared_args, "domain": "health"},
            )
        )
    with pytest.raises(PermissionError, match="tenant_scope_violation"):
        asyncio.run(
            server.call_tool(
                "audit_trace",
                {**shared_args, "item_id": fact_id},
            )
        )


def test_tenant_b_retrieve_returns_only_tenant_b_data(monkeypatch):
    _reset(monkeypatch)

    out = asyncio.run(
        server.call_tool(
            "retrieve_context_pack",
            {
                "_auth_token": "tenant-b-agent",
                "domain": "health",
                "query": "medication",
            },
        )
    )
    payload = json.loads(out[0].text)
    payload_text = json.dumps(payload)

    assert payload["domain"] == "health"
    assert "metformin" in payload_text
    assert "insulin" not in payload_text
