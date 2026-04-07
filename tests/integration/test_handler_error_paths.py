"""Error-path tests for critical tool handlers.

Tests use dev-stdio mode (ORENYL_TRANSPORT=stdio, ORENYL_ALLOW_STDIO_DEV=1) to
bypass authentication and hit handler logic directly. The auth-scope test
stubs the verifier to test authorization enforcement specifically.
"""

import asyncio
import json

import pytest

from orenyl import server


@pytest.fixture(autouse=True)
def _dev_stdio_mode(monkeypatch):
    """Enable dev-stdio for all tests in this module."""
    monkeypatch.setenv("ORENYL_TRANSPORT", "stdio")
    monkeypatch.setenv("ORENYL_ALLOW_STDIO_DEV", "1")


def test_delete_and_recompute_missing_target_id():
    out = asyncio.run(server.call_tool("delete_and_recompute", {"target_type": "event"}))
    payload = json.loads(out[0].text)
    assert payload["ok"] is False


def test_list_events_negative_limit():
    out = asyncio.run(server.call_tool("list_events", {"limit": -1}))
    payload = json.loads(out[0].text)
    assert "events" in payload or "error" in payload


def test_store_event_empty_domains_list():
    """store_event with an empty domains list should not crash."""
    out = asyncio.run(
        server.call_tool(
            "store_event",
            {
                "type": "note",
                "payload": {"text": "hello"},
                "domains": [],
            },
        )
    )
    payload = json.loads(out[0].text)
    assert "stored" in payload or "error" in payload


def test_unauthorized_scope_raises_permission_error(monkeypatch):
    """This test stubs the verifier to test scope enforcement specifically."""
    from mcp.server.auth.provider import AccessToken

    class _ReadOnlyVerifier:
        async def verify_token(self, token):
            if token == "ro":
                return AccessToken(
                    token=token,
                    client_id="test",
                    scopes=["memory:read"],
                    resource=None,
                )
            return None

    monkeypatch.setenv("ORENYL_TRANSPORT", "streamable-http")
    monkeypatch.delenv("ORENYL_ALLOW_STDIO_DEV", raising=False)
    monkeypatch.setattr(server, "_get_token_verifier", lambda: _ReadOnlyVerifier())

    with pytest.raises(PermissionError, match="forbidden"):
        asyncio.run(
            server.call_tool(
                "store_event",
                {
                    "_auth_token": "ro",
                    "type": "note",
                    "payload": {"text": "hello"},
                    "domains": ["general"],
                },
            )
        )
