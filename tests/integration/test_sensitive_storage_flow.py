import asyncio
import json

from lore import server
from lore.context_pack import ContextPackBuilder
from lore.db import Database
from lore.lineage import LineageEngine
from lore.models import Event


def _reset_server(monkeypatch, db):
    monkeypatch.setattr(server, "db", db)
    monkeypatch.setattr(server, "engine", LineageEngine(db))
    monkeypatch.setattr(server, "pack_builder", ContextPackBuilder(db))


def test_high_sensitivity_payload_stored_encrypted_when_key_present(monkeypatch):
    db = Database(":memory:")
    _reset_server(monkeypatch, db)
    monkeypatch.setenv("LORE_ENCRYPTION_PASSPHRASE", "test-passphrase!")
    monkeypatch.setenv("LORE_ENCRYPTION_SALT", "MDEyMzQ1Njc4OWFiY2RlZg==")

    out = asyncio.run(
        server.handle_store_event(
            {
                "domains": ["health"],
                "type": "note",
                "content": "started metformin",
                "sensitivity": "high",
            }
        )
    )
    response = json.loads(out[0].text)
    event_id = response["event_id"]
    event = db.get_event(event_id)

    assert event is not None
    assert event["payload"].get("_encrypted") is True
    assert "ciphertext" in event["payload"]
    assert response["payload"] == {"_encrypted": True}


def test_restricted_not_returned_in_context_pack():
    db = Database(":memory:")
    engine = LineageEngine(db)

    ev = Event(
        id="event:test:restricted",
        type="med_started",
        payload={"name": "secret-med"},
        domains=["health"],
        sensitivity="restricted",
    )
    db.insert_event(ev)
    engine.derive_facts_for_event(db.get_event(ev.id))

    pack = ContextPackBuilder(db).build(domain="health", max_sensitivity="high", query="med")
    assert pack.to_dict().get("facts", []) == []


def test_encryption_enabled_skips_sensitive_fact_derivation(monkeypatch):
    db = Database(":memory:")
    _reset_server(monkeypatch, db)
    monkeypatch.setenv("LORE_ENCRYPTION_PASSPHRASE", "test-passphrase!")
    monkeypatch.setenv("LORE_ENCRYPTION_SALT", "MDEyMzQ1Njc4OWFiY2RlZg==")

    out = asyncio.run(
        server.handle_store_event(
            {
                "domains": ["health"],
                "type": "med_started",
                "payload": {"name": "metformin"},
                "sensitivity": "high",
            }
        )
    )
    event_id = json.loads(out[0].text)["event_id"]
    event = db.get_event(event_id)

    assert event is not None
    assert event["payload"].get("_encrypted") is True

    # Sensitive encrypted events must not derive plaintext-bearing facts.
    facts = db.get_current_facts("active_medications")
    assert facts == []
