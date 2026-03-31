import asyncio
import base64
import json

import pytest

from lore import key_rotation, server
from lore.context_pack import ContextPackBuilder
from lore.db import Database
from lore.encryption import decrypt_content, encrypt_content, resolve_runtime_keyring
from lore.lineage import LineageEngine
from lore.models import Event


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
    monkeypatch.setenv("LORE_ENCRYPTION_PASSPHRASE_V1", "pass-v1-01234567")
    monkeypatch.setenv("LORE_ENCRYPTION_SALT_V1", salt_v1)
    monkeypatch.setenv("LORE_ENCRYPTION_PASSPHRASE", "pass-v1-01234567")
    monkeypatch.setenv("LORE_ENCRYPTION_SALT", salt_v1)

    out = asyncio.run(
        server.handle_store_event(
            {
                "domains": ["health"],
                "type": "note",
                "content": "private record",
                "sensitivity": "high",
            }
        )
    )
    event_id = json.loads(out[0].text)["event_id"]
    stored = db.get_event(event_id)
    assert stored["payload"]["ciphertext"]["key_version"] == "v1"

    monkeypatch.setenv("LORE_ENCRYPTION_KEY_VERSION", "v2")
    monkeypatch.setenv("LORE_ENCRYPTION_PASSPHRASE_V2", "pass-v2-76543210")
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
    monkeypatch.setenv("LORE_ENCRYPTION_PASSPHRASE_V1", "pass-v1-01234567")
    monkeypatch.setenv("LORE_ENCRYPTION_SALT_V1", salt_v1)
    monkeypatch.setenv("LORE_ENCRYPTION_PASSPHRASE", "pass-v1-01234567")
    monkeypatch.setenv("LORE_ENCRYPTION_SALT", salt_v1)

    out = asyncio.run(
        server.handle_store_event(
            {
                "domains": ["health"],
                "type": "note",
                "content": "private record",
                "sensitivity": "high",
            }
        )
    )
    event_id = json.loads(out[0].text)["event_id"]
    event = db.get_event(event_id)
    event["payload"]["ciphertext"]["key_version"] = "v9"
    db.update_event_payload(event_id, event["payload"])

    result = key_rotation.rotate_encrypted_payloads(db, skip_missing_keys=True)
    assert result["rotated"] == 0
    assert result["skipped_missing_keys"] == 1


def test_rotation_job_requires_tenant_scope_in_multi_tenant_mode(monkeypatch):
    db = Database(":memory:")
    monkeypatch.setenv("LORE_ENABLE_MULTI_TENANT", "1")
    monkeypatch.setenv("LORE_ENCRYPTION_PASSPHRASE", "pass-v1-01234567")
    monkeypatch.setenv(
        "LORE_ENCRYPTION_SALT",
        base64.b64encode(b"0123456789abcdef").decode("ascii"),
    )

    with pytest.raises(PermissionError, match="tenant_scope_required"):
        key_rotation.rotate_encrypted_payloads(db)


def test_rotation_job_only_rotates_requested_tenant(monkeypatch):
    db = Database(":memory:")
    _reset_server(monkeypatch, db)
    monkeypatch.setenv("LORE_ENABLE_MULTI_TENANT", "1")

    salt_v1 = base64.b64encode(b"0123456789abcdef").decode("ascii")
    salt_v2 = base64.b64encode(b"fedcba9876543210").decode("ascii")

    monkeypatch.setenv("LORE_ENCRYPTION_KEY_VERSION", "v1")
    monkeypatch.setenv("LORE_ENCRYPTION_PASSPHRASE_V1", "pass-v1-01234567")
    monkeypatch.setenv("LORE_ENCRYPTION_SALT_V1", salt_v1)
    monkeypatch.setenv("LORE_ENCRYPTION_PASSPHRASE", "pass-v1-01234567")
    monkeypatch.setenv("LORE_ENCRYPTION_SALT", salt_v1)
    keyring_v1 = resolve_runtime_keyring()
    active_v1 = keyring_v1.keys[keyring_v1.active_version]

    event_ids = []
    for tenant_id, content in (("tenant-a", "private-a"), ("tenant-b", "private-b")):
        event = Event(
            id=f"event:test:rotation:{tenant_id}",
            type="note",
            payload={
                "_encrypted": True,
                "ciphertext": encrypt_content(
                    content,
                    active_v1.key,
                    salt=active_v1.salt,
                    key_version=keyring_v1.active_version,
                ),
            },
            domains=["health"],
            sensitivity="high",
            tenant_id=tenant_id,
        )
        db.insert_event(event)
        event_ids.append((tenant_id, event.id))

    monkeypatch.setenv("LORE_ENCRYPTION_KEY_VERSION", "v2")
    monkeypatch.setenv("LORE_ENCRYPTION_PASSPHRASE_V2", "pass-v2-76543210")
    monkeypatch.setenv("LORE_ENCRYPTION_SALT_V2", salt_v2)
    server._reset_runtime_state_for_tests()

    result = key_rotation.rotate_encrypted_payloads(db, tenant_id="tenant-a")
    assert result["rotated"] == 1

    tenant_a_event = db.get_event(event_ids[0][1], tenant_id="tenant-a")
    tenant_b_event = db.get_event(event_ids[1][1], tenant_id="tenant-b")
    assert tenant_a_event["payload"]["ciphertext"]["key_version"] == "v2"
    assert tenant_b_event["payload"]["ciphertext"]["key_version"] == "v1"
