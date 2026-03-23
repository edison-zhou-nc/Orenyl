import pytest

from lore.db import Database
from lore.models import Event


def test_event_repository_round_trips_payload_domains_and_updates():
    db = Database(":memory:")
    event = Event(
        id="event:test:repo-e1",
        type="note",
        payload={"text": "hello"},
        domains=["health", "general"],
        metadata={"subject_id": "user:1"},
    )

    db.insert_event(event)
    stored = db.get_event(event.id)

    assert stored is not None
    assert stored["payload"] == {"text": "hello"}
    assert stored["domains"] == ["general", "health"]
    assert db.get_active_domains_by_subject("user:1") == {"general", "health"}

    assert db.update_event_payload(event.id, {"text": "updated"}) is True
    assert db.get_event(event.id)["payload"] == {"text": "updated"}


def test_event_repository_requires_tenant_scope_for_unscoped_methods(monkeypatch):
    db = Database(":memory:")
    event = Event(
        id="event:test:repo-e2",
        type="note",
        payload={"text": "scope"},
        domains=["health"],
        content_hash="hash-e2",
        expires_at="2030-01-01T00:00:00Z",
        tenant_id="tenant-a",
    )
    db.insert_event(event)
    monkeypatch.setenv("LORE_ENABLE_MULTI_TENANT", "1")

    with pytest.raises(PermissionError, match="tenant_scope_required"):
        db.get_all_events()
    with pytest.raises(PermissionError, match="tenant_scope_required"):
        db.find_event_by_content_hash("hash-e2")
    with pytest.raises(PermissionError, match="tenant_scope_required"):
        db.get_expired_events("2031-01-01T00:00:00Z")
    with pytest.raises(PermissionError, match="tenant_scope_required"):
        db.update_event_payload(event.id, {"text": "blocked"})
    with pytest.raises(PermissionError, match="tenant_scope_required"):
        db.update_event_retention(event.id, "warm", None)

    assert db.get_all_events(tenant_id="tenant-a")[0]["id"] == event.id
    assert db.find_event_by_content_hash("hash-e2", tenant_id="tenant-a")["id"] == event.id
    assert db.get_expired_events("2031-01-01T00:00:00Z", tenant_id="tenant-a")[0]["id"] == event.id
    assert db.update_event_payload(event.id, {"text": "scoped"}, tenant_id="tenant-a") is True
    assert db.update_event_retention(event.id, "warm", None, tenant_id="tenant-a") is True
