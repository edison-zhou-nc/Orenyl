from __future__ import annotations

import asyncio
import json

from mcp.server.auth.provider import AccessToken

from lore import server
from lore.context_pack import ContextPackBuilder
from lore.db import Database
from lore.lineage import LineageEngine
from lore.models import Event
from lore.handlers.tooling import list_registered_tools


class _Verifier:
    async def verify_token(self, token: str):
        if token == "ok":
            return AccessToken(
                token=token,
                client_id="agent-a",
                scopes=["memory:read", "memory:write", "memory:delete", "memory:export"],
            )
        return None


def test_phase4_tools_registered_and_callable(monkeypatch):
    db = Database(":memory:")
    monkeypatch.setattr(server, "db", db)
    monkeypatch.setattr(server, "engine", LineageEngine(db))
    monkeypatch.setattr(server, "pack_builder", ContextPackBuilder(db))
    monkeypatch.setattr(server, "_get_token_verifier", lambda: _Verifier())

    names = {tool.name for tool in asyncio.run(server.list_tools())}
    assert names == {
        "store_event",
        "retrieve_context_pack",
        "delete_and_recompute",
        "audit_trace",
        "list_events",
        "export_domain",
        "record_consent",
        "erase_subject_data",
        "export_subject_data",
        "generate_processing_record",
        "audit_anomaly_scan",
        "create_snapshot",
        "verify_snapshot",
        "restore_snapshot",
    }

    consent_out = asyncio.run(
        server.call_tool(
            "record_consent",
            {"_auth_token": "ok", "subject_id": "user:123", "status": "granted"},
        )
    )
    consent_payload = json.loads(consent_out[0].text)
    assert consent_payload["ok"] is True

    db.insert_event(
        Event(
            id="event:test:wiring-u123",
            type="note",
            payload={"text": "hello"},
            metadata={"subject_id": "user:123"},
            domains=["general"],
        )
    )

    export_out = asyncio.run(
        server.call_tool("export_subject_data", {"_auth_token": "ok", "subject_id": "user:123"})
    )
    export_payload = json.loads(export_out[0].text)
    assert export_payload["ok"] is True
    assert export_payload["manifest"]["record_count"] >= 1

    snapshot_out = asyncio.run(
        server.call_tool("create_snapshot", {"_auth_token": "ok", "label": "wire"})
    )
    snapshot_payload = json.loads(snapshot_out[0].text)
    assert snapshot_payload["ok"] is True

    verify_out = asyncio.run(
        server.call_tool(
            "verify_snapshot",
            {"_auth_token": "ok", "snapshot_id": snapshot_payload["snapshot_id"]},
        )
    )
    verify_payload = json.loads(verify_out[0].text)
    assert verify_payload["ok"] is True


def test_retrieve_context_pack_schema_includes_restricted_max_sensitivity():
    tools = {tool.name: tool for tool in list_registered_tools()}
    schema = tools["retrieve_context_pack"].inputSchema
    sensitivity_enum = schema["properties"]["max_sensitivity"]["enum"]

    assert "restricted" in sensitivity_enum
