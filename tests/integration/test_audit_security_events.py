import asyncio
import importlib
import pytest

from lore import audit
from lore import server


def test_authz_deny_writes_audit_record(monkeypatch):
    audit.clear_events()
    monkeypatch.delenv("LORE_AUTH_REQUIRED", raising=False)

    with pytest.raises(PermissionError, match="unauthorized"):
        asyncio.run(server.call_tool("list_events", {}))

    events = audit.get_events()
    assert len(events) >= 1
    assert events[-1]["result"] == "deny"
    assert events[-1]["action"] == "list_events"


def test_authz_deny_writes_request_id(monkeypatch):
    audit.clear_events()
    monkeypatch.delenv("LORE_AUTH_REQUIRED", raising=False)

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
