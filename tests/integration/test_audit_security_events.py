import asyncio
import importlib
import sqlite3

import pytest

from lore import audit, server


class _DenyVerifier:
    async def verify_token(self, token: str):
        return None


def test_authz_deny_writes_audit_record(monkeypatch):
    audit.clear_events()
    monkeypatch.delenv("LORE_AUTH_REQUIRED", raising=False)
    monkeypatch.setattr(server, "_get_token_verifier", lambda: _DenyVerifier())

    with pytest.raises(PermissionError, match="unauthorized"):
        asyncio.run(server.call_tool("list_events", {}))

    events = audit.get_events()
    assert len(events) >= 1
    assert events[-1]["result"] == "deny"
    assert events[-1]["action"] == "list_events"


def test_authz_deny_writes_request_id(monkeypatch):
    audit.clear_events()
    monkeypatch.delenv("LORE_AUTH_REQUIRED", raising=False)
    monkeypatch.setattr(server, "_get_token_verifier", lambda: _DenyVerifier())

    with pytest.raises(PermissionError, match="unauthorized"):
        asyncio.run(server.call_tool("list_events", {"_request_id": "req-123"}))

    events = audit.get_events()
    assert len(events) >= 1
    assert events[-1]["request_id"] == "req-123"


def test_audit_events_persist_across_module_reload(monkeypatch, workspace_tmp_path):
    db_path = workspace_tmp_path / "audit-persist.sqlite3"
    try:
        if db_path.exists():
            db_path.unlink()
        monkeypatch.setenv("LORE_AUDIT_DB_PATH", str(db_path))
        reloaded_audit = importlib.reload(audit)
        reloaded_audit.clear_events()

        reloaded_audit.log_security_event(
            "list_events",
            "deny",
            principal_id="u1",
            request_id="req-persist-1",
            details={"reason": "unauthorized"},
        )

        reloaded_again = importlib.reload(reloaded_audit)
        events = reloaded_again.get_events()
        assert len(events) == 1
        assert events[0]["request_id"] == "req-persist-1"
    finally:
        if db_path.exists():
            try:
                db_path.unlink()
            except PermissionError:
                pass


def test_delete_audit_event_emitted_on_engine_failure(monkeypatch):
    events = []

    class _RaisingEngine:
        def delete_and_recompute(self, *_args, **_kwargs):
            raise RuntimeError("boom")

    def _capture(action, result, principal_id="", request_id="", details=None):
        events.append(
            {
                "action": action,
                "result": result,
                "principal_id": principal_id,
                "request_id": request_id,
                "details": details or {},
            }
        )

    monkeypatch.setattr(server, "engine", _RaisingEngine())
    monkeypatch.setattr(audit, "log_security_event", _capture)

    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(
            server.handle_delete_and_recompute(
                {
                    "_request_id": "req-del-1",
                    "_auth_client_id": "u1",
                    "target_id": "event:x",
                    "target_type": "event",
                    "mode": "soft",
                }
            )
        )

    assert events
    assert events[-1]["action"] == "delete_and_recompute"
    assert events[-1]["result"] == "error"
    assert events[-1]["request_id"] == "req-del-1"


def test_audit_reset_for_tests_reopens_connection_for_new_path(monkeypatch, workspace_tmp_path):
    db1 = workspace_tmp_path / "audit-one.sqlite3"
    db2 = workspace_tmp_path / "audit-two.sqlite3"
    monkeypatch.setenv("LORE_AUDIT_DB_PATH", str(db1))
    audit._reset_for_tests()
    audit.clear_events()
    audit.log_security_event("list_events", "deny", request_id="req-one")

    monkeypatch.setenv("LORE_AUDIT_DB_PATH", str(db2))
    audit._reset_for_tests()
    audit.clear_events()
    audit.log_security_event("list_events", "deny", request_id="req-two")

    with sqlite3.connect(db1) as conn1:
        count1 = conn1.execute("SELECT COUNT(*) FROM security_audit_events").fetchone()[0]
    with sqlite3.connect(db2) as conn2:
        count2 = conn2.execute("SELECT COUNT(*) FROM security_audit_events").fetchone()[0]

    assert count1 == 1
    assert count2 == 1
