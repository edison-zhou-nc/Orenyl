from orenyl import server
from orenyl.db import Database
from orenyl.lineage import LineageEngine
from orenyl.models import Event


def test_expired_event_is_soft_deleted_by_ttl_sweep(monkeypatch):
    db = Database(":memory:")
    engine = LineageEngine(db)
    event = Event(
        id="event:test:ttl-soft",
        type="note",
        payload={"text": "expired"},
        domains=["general"],
        expires_at="2000-01-01T00:00:00Z",
    )
    db.insert_event(event)

    monkeypatch.setattr(server, "db", db)
    monkeypatch.setattr(server, "engine", engine)

    out = server.run_ttl_sweep(delete_mode="soft")

    assert out["count"] == 1
    assert event.id in out["event_ids"]
    stored = db.get_event(event.id)
    assert stored is not None
    assert stored["deleted_at"] is not None


def test_expired_event_is_hard_deleted_by_ttl_sweep(monkeypatch):
    db = Database(":memory:")
    engine = LineageEngine(db)
    event = Event(
        id="event:test:ttl-hard",
        type="note",
        payload={"text": "expired"},
        domains=["general"],
        expires_at="2000-01-01T00:00:00Z",
    )
    db.insert_event(event)

    monkeypatch.setattr(server, "db", db)
    monkeypatch.setattr(server, "engine", engine)

    out = server.run_ttl_sweep(delete_mode="hard")

    assert out["count"] == 1
    assert event.id in out["event_ids"]
    assert db.get_event(event.id) is None


def test_multi_tenant_ttl_sweep_processes_expired_events_without_tenant_error(monkeypatch):
    db = Database(":memory:")
    engine = LineageEngine(db)
    tenant_a = Event(
        id="event:test:ttl-tenant-a",
        type="note",
        payload={"text": "expired-a"},
        domains=["general"],
        expires_at="2000-01-01T00:00:00Z",
        tenant_id="tenant-a",
    )
    tenant_b = Event(
        id="event:test:ttl-tenant-b",
        type="note",
        payload={"text": "expired-b"},
        domains=["general"],
        expires_at="2000-01-01T00:00:00Z",
        tenant_id="tenant-b",
    )
    db.insert_event(tenant_a)
    db.insert_event(tenant_b)

    monkeypatch.setattr(server, "db", db)
    monkeypatch.setattr(server, "engine", engine)
    monkeypatch.setenv("ORENYL_ENABLE_MULTI_TENANT", "1")

    out = server.run_ttl_sweep(delete_mode="soft")

    assert out["count"] == 2
    assert set(out["event_ids"]) == {tenant_a.id, tenant_b.id}
