from __future__ import annotations

import asyncio
import json

from mcp.server.auth.provider import AccessToken

from orenyl import server


def test_write_tools_blocked_in_read_only_mode(monkeypatch):
    class _AllowVerifier:
        async def verify_token(self, token: str):
            if token == "allow":
                return AccessToken(token=token, client_id="u1", scopes=["memory:write"])
            return None

    monkeypatch.setenv("ORENYL_READ_ONLY_MODE", "1")
    monkeypatch.setattr(server, "_get_token_verifier", lambda: _AllowVerifier())

    out = asyncio.run(
        server.call_tool(
            "store_event",
            {
                "_auth_token": "allow",
                "domains": ["general"],
                "type": "note",
                "payload": {"text": "blocked by read-only mode"},
            },
        )
    )
    payload = json.loads(out[0].text)
    assert payload["ok"] is False
    assert "ORENYL_READ_ONLY_MODE" in payload["error"]["message"]

    consent_out = asyncio.run(
        server.call_tool(
            "record_consent",
            {
                "_auth_token": "allow",
                "subject_id": "user:1",
                "status": "granted",
            },
        )
    )
    consent_payload = json.loads(consent_out[0].text)
    assert consent_payload["ok"] is False
    assert "ORENYL_READ_ONLY_MODE" in consent_payload["error"]["message"]
