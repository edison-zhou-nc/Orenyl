import asyncio
import json

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
