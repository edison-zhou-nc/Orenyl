import asyncio
import json

import pytest

from lore import retention, server
from lore.context_pack import ContextPackBuilder
from lore.db import Database
from lore.lineage import LineageEngine
from lore.models import Event


def _reset_server(monkeypatch, db):
    monkeypatch.setattr(server, "db", db)
    monkeypatch.setattr(server, "engine", LineageEngine(db))
    monkeypatch.setattr(server, "pack_builder", ContextPackBuilder(db))


def test_archive_tier_excludes_from_context_pack_but_keeps_export(monkeypatch):
    db = Database(":memory:")
    _reset_server(monkeypatch, db)
    ev = Event(
        id="event:test:retention",
        type="med_started",
        payload={"name": "metformin"},
        domains=["health"],
        ts="2026-01-01T00:00:00Z",
    )
    db.insert_event(ev)
    server.engine.derive_facts_for_event(db.get_event(ev.id))

    retention.apply_retention_to_db(
        db,
        now_ts="2026-01-10T00:00:00Z",
        policies={"health": {"warm_days": 1, "archive_days": 3, "delete_days": 99}},
    )

    event = db.get_event(ev.id)
    assert event["retention_tier"] == "archive"
    assert event["archived_at"] is not None

    pack = ContextPackBuilder(db).build(domain="health", query="med")
    assert pack.to_dict()["facts"] == []

    out = asyncio.run(server.handle_export_domain({"domain": "health", "format": "json"}))
    exported = json.loads(out[0].text)
    assert any(item["id"] == ev.id for item in exported["events"])


def test_retention_updated_count_does_not_increment_on_noop_delete(monkeypatch):
    db = Database(":memory:")
    _reset_server(monkeypatch, db)
    ev = Event(
        id="event:test:retention-noop",
        type="note",
        payload={"text": "noop"},
        domains=["health"],
        ts="2026-01-01T00:00:00Z",
    )
    db.insert_event(ev)

    monkeypatch.setattr(db, "soft_delete_event", lambda *_args, **_kwargs: False)
    out = retention.apply_retention_to_db(
        db,
        now_ts="2026-01-10T00:00:00Z",
        policies={"health": {"warm_days": 1, "archive_days": 3, "delete_days": 7}},
    )
    assert out["deleted"] == 0
    assert out["updated"] == 0


def test_retention_requires_tenant_scope_in_multi_tenant_mode(monkeypatch):
    db = Database(":memory:")
    monkeypatch.setenv("LORE_ENABLE_MULTI_TENANT", "1")

    with pytest.raises(PermissionError, match="tenant_scope_required"):
        retention.apply_retention_to_db(
            db,
            now_ts="2026-01-10T00:00:00Z",
            policies={"default": {"delete_days": 1}},
        )


def test_retention_only_updates_requested_tenant(monkeypatch):
    db = Database(":memory:")
    _reset_server(monkeypatch, db)
    monkeypatch.setenv("LORE_ENABLE_MULTI_TENANT", "1")

    tenant_a_event = Event(
        id="event:test:retention-tenant-a",
        type="note",
        payload={"text": "tenant-a"},
        domains=["health"],
        tenant_id="tenant-a",
        ts="2026-01-01T00:00:00Z",
    )
    tenant_b_event = Event(
        id="event:test:retention-tenant-b",
        type="note",
        payload={"text": "tenant-b"},
        domains=["health"],
        tenant_id="tenant-b",
        ts="2026-01-01T00:00:00Z",
    )
    db.insert_event(tenant_a_event)
    db.insert_event(tenant_b_event)

    out = retention.apply_retention_to_db(
        db,
        now_ts="2026-01-10T00:00:00Z",
        policies={"health": {"warm_days": 1, "archive_days": 3, "delete_days": 7}},
        tenant_id="tenant-a",
    )

    assert out["deleted"] == 1
    assert db.get_event(tenant_a_event.id, tenant_id="tenant-a")["deleted_at"] is not None
    assert db.get_event(tenant_b_event.id, tenant_id="tenant-b")["deleted_at"] is None
