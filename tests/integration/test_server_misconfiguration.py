import asyncio
import json

import pytest
from mcp.server.auth.provider import AccessToken

from orenyl import env_vars, server


def test_call_tool_masks_token_verifier_runtime_error(monkeypatch):
    attempts = {"count": 0}

    def _raise_misconfig():
        attempts["count"] += 1
        raise RuntimeError(f"{env_vars.OIDC_ISSUER} must be set when RS256/JWKS is enabled")

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


def test_call_tool_dev_stdio_bypasses_token_verifier_bootstrap(monkeypatch):
    server._reset_runtime_state_for_tests()
    monkeypatch.setenv("ORENYL_TRANSPORT", "stdio")
    monkeypatch.setenv("ORENYL_ALLOW_STDIO_DEV", "1")

    def _raise_misconfig():
        raise AssertionError("token verifier bootstrap should be skipped in dev stdio mode")

    monkeypatch.setattr(server, "build_token_verifier_from_env", _raise_misconfig)
    out = asyncio.run(server.call_tool("list_events", {}))

    payload = json.loads(out[0].text)
    assert payload["count"] == 0
    assert payload["events"] == []


def test_call_tool_domain_runtime_error_is_not_remapped(monkeypatch):
    class _AllowVerifier:
        async def verify_token(self, token: str):
            if token == "allow":
                return AccessToken(token=token, client_id="u1", scopes=["memory:write"])
            return None

    monkeypatch.setattr(server, "_get_token_verifier", lambda: _AllowVerifier())
    monkeypatch.setenv(env_vars.ENCRYPTION_PASSPHRASE, "top-secret-passphrase")
    monkeypatch.delenv(env_vars.ENCRYPTION_SALT, raising=False)
    monkeypatch.delenv(env_vars.ALLOW_INSECURE_DEV_SALT, raising=False)

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
    assert payload["error"]["type"] == "internal_error"
    assert "server_misconfigured" not in payload["error"]["message"]
    assert f"{env_vars.ENCRYPTION_SALT} is required" in payload["error"]["message"]


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
    assert payload["error"]["type"] == "internal_error"
    assert payload["error"]["message"] == "internal_error; see server logs"


def test_call_tool_uses_env_var_registry_to_pass_through_runtime_errors(monkeypatch):
    class _AllowDeleteVerifier:
        async def verify_token(self, token: str):
            if token == "allow":
                return AccessToken(token=token, client_id="u1", scopes=["memory:delete"])
            return None

    class _RaisingEngine:
        def delete_and_recompute(self, *_args, **_kwargs):
            raise RuntimeError("CUSTOM_ENV is required")

    monkeypatch.setattr(server, "_get_token_verifier", lambda: _AllowDeleteVerifier())
    monkeypatch.setattr(server, "engine", _RaisingEngine())
    monkeypatch.setattr(env_vars, "all_names", lambda: ("CUSTOM_ENV",))

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
    assert payload["error"]["message"] == "CUSTOM_ENV is required"


def test_call_tool_masks_policy_shadow_mode_misconfiguration(monkeypatch):
    class _AllowVerifier:
        async def verify_token(self, token: str):
            if token == "allow":
                return AccessToken(
                    token=token,
                    client_id="agent-a",
                    scopes=["memory:read"],
                    resource="tenant-a",
                )
            return None

    server._reset_runtime_state_for_tests()
    monkeypatch.setenv("ORENYL_ENABLE_MULTI_TENANT", "1")
    monkeypatch.setenv("ORENYL_ENABLE_AGENT_PERMISSIONS", "1")
    monkeypatch.setenv("ORENYL_POLICY_SHADOW_MODE", "1")
    monkeypatch.setattr(server, "_get_token_verifier", lambda: _AllowVerifier())

    with pytest.raises(PermissionError, match="server_misconfigured"):
        asyncio.run(server.call_tool("list_events", {"_auth_token": "allow", "domain": "general"}))
