import asyncio
import base64
import json

from lore import key_rotation, server
from lore.context_pack import ContextPackBuilder
from lore.db import Database
from lore.encryption import decrypt_content, resolve_runtime_keyring
from lore.lineage import LineageEngine


def _reset_server(monkeypatch, db):
    monkeypatch.setattr(server, "db", db)
    monkeypatch.setattr(server, "engine", LineageEngine(db))
    monkeypatch.setattr(server, "pack_builder", ContextPackBuilder(db))
    server._reset_runtime_state_for_tests()


def test_rotation_job_reencrypts_old_version_payloads(monkeypatch):
    db = Database(":memory:")
    _reset_server(monkeypatch, db)

    salt_v1 = base64.b64encode(b"0123456789abcdef").decode("ascii")
    salt_v2 = base64.b64encode(b"fedcba9876543210").decode("ascii")

    monkeypatch.setenv("LORE_ENCRYPTION_KEY_VERSION", "v1")
    monkeypatch.setenv("LORE_ENCRYPTION_PASSPHRASE_V1", "pass-v1")
    monkeypatch.setenv("LORE_ENCRYPTION_SALT_V1", salt_v1)
    monkeypatch.setenv("LORE_ENCRYPTION_PASSPHRASE", "pass-v1")
    monkeypatch.setenv("LORE_ENCRYPTION_SALT", salt_v1)

    out = asyncio.run(server.handle_store_event({
        "domains": ["health"],
        "type": "note",
        "content": "private record",
        "sensitivity": "high",
    }))
    event_id = json.loads(out[0].text)["event_id"]
    stored = db.get_event(event_id)
    assert stored["payload"]["ciphertext"]["key_version"] == "v1"

    monkeypatch.setenv("LORE_ENCRYPTION_KEY_VERSION", "v2")
    monkeypatch.setenv("LORE_ENCRYPTION_PASSPHRASE_V2", "pass-v2")
    monkeypatch.setenv("LORE_ENCRYPTION_SALT_V2", salt_v2)
    server._reset_runtime_state_for_tests()

    result = key_rotation.rotate_encrypted_payloads(db)
    assert result["rotated"] == 1

    rotated = db.get_event(event_id)
    envelope = rotated["payload"]["ciphertext"]
    assert envelope["key_version"] == "v2"

    keyring = resolve_runtime_keyring()
    active_key = keyring.keys[keyring.active_version]
    assert decrypt_content(envelope, active_key.key) == "private record"


def test_rotation_job_can_skip_missing_key_versions(monkeypatch):
    db = Database(":memory:")
    _reset_server(monkeypatch, db)

    salt_v1 = base64.b64encode(b"0123456789abcdef").decode("ascii")
    monkeypatch.setenv("LORE_ENCRYPTION_KEY_VERSION", "v1")
    monkeypatch.setenv("LORE_ENCRYPTION_PASSPHRASE_V1", "pass-v1")
    monkeypatch.setenv("LORE_ENCRYPTION_SALT_V1", salt_v1)
    monkeypatch.setenv("LORE_ENCRYPTION_PASSPHRASE", "pass-v1")
    monkeypatch.setenv("LORE_ENCRYPTION_SALT", salt_v1)

    out = asyncio.run(server.handle_store_event({
        "domains": ["health"],
        "type": "note",
        "content": "private record",
        "sensitivity": "high",
    }))
    event_id = json.loads(out[0].text)["event_id"]
    event = db.get_event(event_id)
    event["payload"]["ciphertext"]["key_version"] = "v9"
    db.update_event_payload(event_id, event["payload"])

    result = key_rotation.rotate_encrypted_payloads(db, skip_missing_keys=True)
    assert result["rotated"] == 0
    assert result["skipped_missing_keys"] == 1
