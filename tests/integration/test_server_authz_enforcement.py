import asyncio
import json

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
        if token == "tenant-a":
            return AccessToken(
                token=token,
                client_id="tenant-a",
                scopes=["memory:read", "memory:write", "memory:delete"],
                resource="tenant-a",
            )
        if token == "tenant-b":
            return AccessToken(
                token=token,
                client_id="tenant-b",
                scopes=["memory:read", "memory:write", "memory:delete"],
                resource="tenant-b",
            )
        if token == "read":
            return AccessToken(
                token=token, client_id="u1", scopes=["memory:read"], resource="tenant-a"
            )
        if token == "export":
            return AccessToken(
                token=token, client_id="u1", scopes=["memory:export"], resource="tenant-a"
            )
        if token == "admin":
            return AccessToken(
                token=token,
                client_id="u1",
                scopes=[
                    "memory:read",
                    "memory:write",
                    "memory:delete",
                    "memory:export",
                    "memory:export:restricted",
                ],
                resource="tenant-a",
            )
        return None


def _reset_server_state(monkeypatch):
    monkeypatch.setenv("LORE_ENABLE_MULTI_TENANT", "1")
    fresh_db = Database(":memory:")
    monkeypatch.setattr(server, "db", fresh_db)
    monkeypatch.setattr(server, "engine", LineageEngine(fresh_db))
    monkeypatch.setattr(server, "pack_builder", ContextPackBuilder(fresh_db))
    verifier = StubVerifier()
    monkeypatch.setattr(server, "_get_token_verifier", lambda: verifier)


def _reset_local_dev_state(monkeypatch):
    monkeypatch.delenv("LORE_ENABLE_MULTI_TENANT", raising=False)
    monkeypatch.setenv("LORE_TRANSPORT", "stdio")
    monkeypatch.setenv("LORE_ALLOW_STDIO_DEV", "1")
    fresh_db = Database(":memory:")
    monkeypatch.setattr(server, "db", fresh_db)
    monkeypatch.setattr(server, "engine", LineageEngine(fresh_db))
    monkeypatch.setattr(server, "pack_builder", ContextPackBuilder(fresh_db))
    server._reset_runtime_state_for_tests()


def test_store_event_persists_resolved_tenant_id(monkeypatch):
    _reset_server_state(monkeypatch)

    out = asyncio.run(
        server.call_tool(
            "store_event",
            {
                "_auth_token": "tenant-a",
                "domains": ["general"],
                "type": "note",
                "payload": {"text": "hello"},
            },
        )
    )
    payload = json.loads(out[0].text)
    row = server.db.conn.execute(
        "SELECT tenant_id FROM events WHERE id = ?",
        (payload["event_id"],),
    ).fetchone()

    assert row is not None
    assert row["tenant_id"] == "tenant-a"


def test_delete_and_recompute_cannot_cross_tenants(monkeypatch):
    _reset_server_state(monkeypatch)
    ev = Event(
        id="event:test:tenant-b",
        type="note",
        payload={"text": "secret"},
        domains=["general"],
        tenant_id="tenant-b",
    )
    server.db.insert_event(ev)

    out = asyncio.run(
        server.call_tool(
            "delete_and_recompute",
            {
                "_auth_token": "tenant-a",
                "target_id": ev.id,
                "target_type": "event",
            },
        )
    )
    payload = json.loads(out[0].text)

    assert payload["checks"]["error"] == "Event not found or already deleted"
    assert server.db.get_event(ev.id, tenant_id="tenant-b") is not None


def test_audit_trace_cannot_cross_tenants(monkeypatch):
    _reset_server_state(monkeypatch)
    ev = Event(
        id="event:test:tenant-b:audit",
        type="note",
        payload={"text": "secret"},
        domains=["general"],
        tenant_id="tenant-b",
    )
    server.db.insert_event(ev)

    out = asyncio.run(
        server.call_tool(
            "audit_trace",
            {
                "_auth_token": "tenant-a",
                "item_id": ev.id,
            },
        )
    )
    payload = json.loads(out[0].text)

    assert payload["item_type"] == "unknown"
    assert payload["item_data"] is None
    assert payload["upstream"] == []
    assert payload["downstream"] == []


def test_call_tool_denies_when_no_token(monkeypatch):
    _reset_server_state(monkeypatch)
    audit.clear_events()

    with pytest.raises(PermissionError, match="unauthorized"):
        asyncio.run(server.call_tool("list_events", {}))

    assert any(e["result"] == "deny" and e["action"] == "list_events" for e in audit.get_events())


def test_call_tool_allows_dev_stdio_without_token(monkeypatch):
    _reset_local_dev_state(monkeypatch)
    audit.clear_events()

    out = asyncio.run(server.call_tool("list_events", {}))
    payload = json.loads(out[0].text)

    assert payload["count"] == 0
    assert payload["events"] == []
    assert any(
        e["result"] == "allow"
        and e["action"] == "list_events"
        and e["principal_id"] == "local-dev"
        and e["details"].get("auth_mode") == "dev-stdio"
        for e in audit.get_events()
    )


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
        tenant_id="tenant-a",
    )
    server.db.insert_event(ev)
    server.engine.derive_facts_for_event(server.db.get_event(ev.id))

    with pytest.raises(PermissionError, match="forbidden"):
        asyncio.run(
            server.call_tool(
                "export_domain",
                {
                    "domain": "health",
                    "format": "json",
                    "confirm_restricted": True,
                    "_auth_token": "export",
                },
            )
        )
