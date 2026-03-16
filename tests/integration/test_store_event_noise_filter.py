import asyncio
import json

from mcp.server.auth.provider import AccessToken

from lore import server
from lore.context_pack import ContextPackBuilder
from lore.db import Database
from lore.lineage import LineageEngine


def _reset_server(monkeypatch, db):
    monkeypatch.setattr(server, "db", db)
    monkeypatch.setattr(server, "engine", LineageEngine(db))
    monkeypatch.setattr(server, "pack_builder", ContextPackBuilder(db))


def test_store_event_rejects_sensitive_credentials(monkeypatch):
    db = Database(":memory:")
    _reset_server(monkeypatch, db)

    out = asyncio.run(
        server.handle_store_event(
            {
                "domains": ["general"],
                "content": "password: hunter2",
                "type": "note",
                "payload": {},
            }
        )
    )
    payload = json.loads(out[0].text)
    assert payload["stored"] is False
    assert payload["reason"] == "sensitive_credential_or_identifier"


def test_store_event_allows_short_structured_payload(monkeypatch):
    db = Database(":memory:")
    _reset_server(monkeypatch, db)

    out = asyncio.run(
        server.handle_store_event(
            {
                "domains": ["general"],
                "type": "note",
                "payload": {"key": "ok"},
            }
        )
    )
    payload = json.loads(out[0].text)
    assert payload["stored"] is True
    assert "event_id" in payload


def test_call_tool_path_rejects_noise_filtered_content(monkeypatch):
    class _AllowAllVerifier:
        async def verify_token(self, token: str):
            if token == "allow":
                return AccessToken(
                    token=token,
                    client_id="u1",
                    scopes=["memory:write", "memory:read", "memory:delete", "memory:export"],
                )
            return None

    verifier = _AllowAllVerifier()
    db = Database(":memory:")
    _reset_server(monkeypatch, db)
    monkeypatch.setattr(server, "_get_token_verifier", lambda: verifier)

    out = asyncio.run(
        server.call_tool(
            "store_event",
            {
                "_auth_token": "allow",
                "domains": ["general"],
                "type": "note",
                "content": "password: hunter2",
                "payload": {},
            },
        )
    )
    payload = json.loads(out[0].text)
    assert payload["stored"] is False
    assert payload["reason"] == "sensitive_credential_or_identifier"


def test_store_event_rejects_sensitive_payload_without_content(monkeypatch):
    db = Database(":memory:")
    _reset_server(monkeypatch, db)

    out = asyncio.run(
        server.handle_store_event(
            {
                "domains": ["general"],
                "type": "note",
                "payload": {"card": "4111 1111 1111 1111"},
            }
        )
    )
    payload = json.loads(out[0].text)
    assert payload["stored"] is False
    assert payload["reason"] == "sensitive_credential_or_identifier"
