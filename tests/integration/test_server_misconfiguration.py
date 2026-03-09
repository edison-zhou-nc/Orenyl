import asyncio
import json
import pytest
from mcp.server.auth.provider import AccessToken

from lore import server


def test_call_tool_masks_token_verifier_runtime_error(monkeypatch):
    attempts = {"count": 0}

    def _raise_misconfig():
        attempts["count"] += 1
        raise RuntimeError("LORE_OIDC_ISSUER must be set when RS256/JWKS is enabled")

    server._reset_runtime_state_for_tests()
    monkeypatch.setattr(server, "build_token_verifier_from_env", _raise_misconfig)

    with pytest.raises(PermissionError, match="server_misconfigured"):
        asyncio.run(server.call_tool("list_events", {}))
    with pytest.raises(PermissionError, match="server_misconfigured"):
        asyncio.run(server.call_tool("list_events", {}))

    assert attempts["count"] == 1


def test_call_tool_masks_token_verifier_non_runtime_error(monkeypatch):
    attempts = {"count": 0}

    def _raise_misconfig():
        attempts["count"] += 1
        raise ValueError("bad OIDC numeric env")

    server._reset_runtime_state_for_tests()
    monkeypatch.setattr(server, "build_token_verifier_from_env", _raise_misconfig)

    with pytest.raises(PermissionError, match="server_misconfigured"):
        asyncio.run(server.call_tool("list_events", {}))
    with pytest.raises(PermissionError, match="server_misconfigured"):
        asyncio.run(server.call_tool("list_events", {}))

    assert attempts["count"] == 1


def test_call_tool_domain_runtime_error_is_not_remapped(monkeypatch):
    class _AllowVerifier:
        async def verify_token(self, token: str):
            if token == "allow":
                return AccessToken(token=token, client_id="u1", scopes=["memory:write"])
            return None

    monkeypatch.setattr(server, "_get_token_verifier", lambda: _AllowVerifier())
    monkeypatch.setenv("LORE_ENCRYPTION_PASSPHRASE", "top-secret-passphrase")
    monkeypatch.delenv("LORE_ENCRYPTION_SALT", raising=False)
    monkeypatch.delenv("LORE_ALLOW_INSECURE_DEV_SALT", raising=False)

    out = asyncio.run(
        server.call_tool(
            "store_event",
            {
                "_auth_token": "allow",
                "domains": ["general"],
                "type": "note",
                "payload": {"text": "sensitive payload"},
                "sensitivity": "high",
            },
        )
    )
    payload = json.loads(out[0].text)
    assert payload["stored"] is False
    assert payload["error"]["type"] == "RuntimeError"
    assert "server_misconfigured" not in payload["error"]["message"]
    assert "LORE_ENCRYPTION_SALT is required" in payload["error"]["message"]


def test_call_tool_sanitizes_non_config_internal_errors(monkeypatch):
    class _AllowDeleteVerifier:
        async def verify_token(self, token: str):
            if token == "allow":
                return AccessToken(token=token, client_id="u1", scopes=["memory:delete"])
            return None

    class _RaisingEngine:
        def delete_and_recompute(self, *_args, **_kwargs):
            raise RuntimeError("SELECT * FROM private_table")

    monkeypatch.setattr(server, "_get_token_verifier", lambda: _AllowDeleteVerifier())
    monkeypatch.setattr(server, "engine", _RaisingEngine())
    out = asyncio.run(
        server.call_tool(
            "delete_and_recompute",
            {
                "_auth_token": "allow",
                "target_id": "event:test",
                "target_type": "event",
            },
        )
    )

    payload = json.loads(out[0].text)
    assert payload["ok"] is False
    assert payload["error"]["type"] == "RuntimeError"
    assert payload["error"]["message"] == "internal_error; see server logs"
