import asyncio
import json

from orenyl import server
from orenyl.context_pack import ContextPackBuilder
from orenyl.db import Database
from orenyl.encryption import decrypt_content, encrypt_content, generate_key
from orenyl.lineage import LineageEngine
from orenyl.models import Event


def _reset_server(monkeypatch, db):
    monkeypatch.setattr(server, "db", db)
    monkeypatch.setattr(server, "engine", LineageEngine(db))
    monkeypatch.setattr(server, "pack_builder", ContextPackBuilder(db))


def test_encryption_hooks_use_aes_gcm():
    salt = b"0123456789abcdef"
    key = generate_key("pw", salt)
    payload = encrypt_content("hello", key, salt=salt)
    assert payload["alg"] == "aes-256-gcm"
    assert decrypt_content(payload, key) == "hello"


def test_list_events_include_tombstoned_returns_deleted_events(monkeypatch):
    db = Database(":memory:")
    _reset_server(monkeypatch, db)

    ev = Event(id="event:test:del", type="diet_preference", payload={"value": "vegan"})
    db.insert_event(ev)
    db.soft_delete_event(ev.id, "2026-01-01T00:00:00Z")

    out = asyncio.run(server.handle_list_events({"include_tombstoned": True}))
    data = json.loads(out[0].text)
    assert data["count"] == 1
    assert data["events"][0]["id"] == ev.id
    assert data["events"][0]["deleted_at"] is not None


def test_context_pack_applies_max_sensitivity_filter():
    db = Database(":memory:")
    engine = LineageEngine(db)

    ev = Event(
        id="event:test:sensitive",
        type="med_started",
        payload={"name": "secret-med"},
        sensitivity="high",
    )
    db.insert_event(ev)
    engine.derive_facts_for_event(db.get_event(ev.id))

    pack = ContextPackBuilder(db).build(domain="general", max_sensitivity="low", limit=50)
    assert pack.to_dict()["facts"] == []


def test_audit_trace_include_source_events_changes_payload(monkeypatch):
    db = Database(":memory:")
    _reset_server(monkeypatch, db)

    ev = Event(id="event:test:trace", type="med_started", payload={"name": "metformin"})
    db.insert_event(ev)
    server.engine.derive_facts_for_event(db.get_event(ev.id))
    fact_id = db.get_current_facts("active_medications")[0]["id"]

    off = asyncio.run(
        server.handle_audit_trace({"item_id": fact_id, "include_source_events": False})
    )
    on = asyncio.run(server.handle_audit_trace({"item_id": fact_id, "include_source_events": True}))
    data_off = json.loads(off[0].text)
    data_on = json.loads(on[0].text)

    assert data_off != data_on
    assert all(node["data"] is None for node in data_off["upstream"] if node["type"] == "event")
    assert any(node["data"] is not None for node in data_on["upstream"] if node["type"] == "event")


def test_export_domain_is_domain_scoped(monkeypatch):
    db = Database(":memory:")
    _reset_server(monkeypatch, db)

    e1 = Event(
        id="event:test:health",
        type="med_started",
        payload={"name": "metformin"},
        domains=["health"],
    )
    e2 = Event(
        id="event:test:career",
        type="role_assigned",
        payload={"user": "u", "role": "admin"},
        domains=["career"],
    )
    db.insert_event(e1)
    db.insert_event(e2)
    server.engine.derive_facts_for_event(db.get_event(e1.id))
    server.engine.derive_facts_for_event(db.get_event(e2.id))

    out = asyncio.run(server.handle_export_domain({"domain": "career"}))
    data = json.loads(out[0].text)
    keys = {f["key"] for f in data["facts"]}
    assert "current_role" in keys
    assert "active_medications" not in keys
    assert "edges" in data
    assert isinstance(data["edges"], list)
    assert "summary" in data


def test_export_domain_markdown_and_timeline_use_real_newlines(monkeypatch):
    db = Database(":memory:")
    _reset_server(monkeypatch, db)

    ev = Event(
        id="event:test:md",
        type="diet_preference",
        payload={"value": "vegan"},
        domains=["preferences"],
        ts="2026-01-01T00:00:00Z",
    )
    db.insert_event(ev)
    server.engine.derive_facts_for_event(db.get_event(ev.id))

    md = asyncio.run(server.handle_export_domain({"domain": "preferences", "format": "markdown"}))[
        0
    ].text
    tl = asyncio.run(server.handle_export_domain({"domain": "preferences", "format": "timeline"}))[
        0
    ].text

    assert "\n" in md
    assert "\\n" not in md
    assert "\n" in tl
    assert "\\n" not in tl


def test_hard_delete_records_tombstone_even_after_erasure():
    db = Database(":memory:")
    engine = LineageEngine(db)
    ev = Event(id="event:test:hard2", type="diet_preference", payload={"value": "vegan"})
    db.insert_event(ev)

    engine.delete_and_recompute(ev.id, "event", reason="gdpr", mode="hard")

    tombstones = db.get_tombstones(ev.id)
    assert len(tombstones) == 1
    assert db.get_event(ev.id) is None
