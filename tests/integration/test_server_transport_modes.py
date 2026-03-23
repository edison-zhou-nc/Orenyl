import asyncio

import pytest
from mcp.server.auth.provider import AccessToken

from lore import audit, server
from lore.context_pack import ContextPackBuilder
from lore.db import Database
from lore.lineage import LineageEngine


def test_default_transport_is_streamable_http_for_prod(monkeypatch):
    monkeypatch.delenv("LORE_TRANSPORT", raising=False)
    assert server.get_transport_mode() == "streamable-http"


def test_stdio_mode_allowed_only_with_explicit_dev_flag(monkeypatch):
    monkeypatch.setenv("LORE_TRANSPORT", "stdio")
    monkeypatch.delenv("LORE_ALLOW_STDIO_DEV", raising=False)

    with pytest.raises(PermissionError, match="LORE_ALLOW_STDIO_DEV=1"):
        server.validate_transport_mode(server.get_transport_mode())

    monkeypatch.setenv("LORE_ALLOW_STDIO_DEV", "1")
    server.validate_transport_mode(server.get_transport_mode())


def test_main_skips_token_bootstrap_in_dev_stdio_mode(monkeypatch):
    called = {"stdio": False}

    async def _fake_run_stdio_server():
        called["stdio"] = True

    def _raise_if_called():
        raise AssertionError("token verifier bootstrap should be skipped in dev stdio mode")

    monkeypatch.setenv("LORE_TRANSPORT", "stdio")
    monkeypatch.setenv("LORE_ALLOW_STDIO_DEV", "1")
    monkeypatch.delenv("LORE_OIDC_ISSUER", raising=False)
    monkeypatch.delenv("LORE_OIDC_JWKS_URL", raising=False)
    monkeypatch.setattr(server, "_get_token_verifier", _raise_if_called)
    monkeypatch.setattr(server, "run_stdio_server", _fake_run_stdio_server)

    server.main()

    assert called["stdio"] is True


def test_streamable_http_server_registers_expected_tools():
    fast = server.build_fastmcp_server()
    names = {tool.name for tool in asyncio.run(fast.list_tools())}
    assert {
        "store_event",
        "retrieve_context_pack",
        "delete_and_recompute",
        "audit_trace",
        "list_events",
        "export_domain",
        "erase_subject_data",
        "export_subject_data",
        "record_consent",
        "generate_processing_record",
        "audit_anomaly_scan",
        "create_snapshot",
        "verify_snapshot",
        "restore_snapshot",
    } <= names


def test_streamable_http_tool_call_logs_single_allow_event(monkeypatch):
    class _AllowVerifier:
        async def verify_token(self, token: str):
            if token == "ok":
                return AccessToken(token=token, client_id="u1", scopes=["memory:read"])
            return None

    db = Database(":memory:")
    monkeypatch.setattr(server, "db", db)
    monkeypatch.setattr(server, "engine", LineageEngine(db))
    monkeypatch.setattr(server, "pack_builder", ContextPackBuilder(db))
    monkeypatch.setattr(server, "_get_token_verifier", lambda: _AllowVerifier())
    audit.clear_events()

    fast = server.build_fastmcp_server()
    asyncio.run(fast.call_tool("list_events", {"auth_token": "ok"}))

    allows = [
        event
        for event in audit.get_events()
        if event["action"] == "list_events" and event["result"] == "allow"
    ]
    assert len(allows) == 1
