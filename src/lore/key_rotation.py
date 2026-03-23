"""Encryption key rotation utilities for encrypted event payloads."""

from __future__ import annotations

import logging

from .db import Database
from .encryption import decrypt_content, encrypt_content, resolve_runtime_keyring

logger = logging.getLogger(__name__)


def rotate_encrypted_payloads(
    db: Database,
    skip_missing_keys: bool = False,
    tenant_id: str = "",
) -> dict[str, int]:
    """Re-encrypt high/restricted event payload envelopes to active key version."""
    tenant_id = db._require_tenant_scope(tenant_id)
    keyring = resolve_runtime_keyring()
    active_version = keyring.active_version
    active_key = keyring.keys[active_version]

    scanned = 0
    rotated = 0
    skipped_missing_keys = 0
    for event in db.get_active_events(tenant_id=tenant_id):
        payload = event.get("payload") or {}
        if not payload.get("_encrypted"):
            continue
        scanned += 1
        envelope = payload.get("ciphertext") or {}
        source_version = str(envelope.get("key_version") or "v1")
        if source_version == active_version:
            continue
        if source_version not in keyring.keys:
            if not skip_missing_keys:
                raise RuntimeError(f"missing_key_version:{source_version}")
            skipped_missing_keys += 1
            logger.warning(
                "key_rotation_missing_source_key event_id=%s source_version=%s",
                event.get("id"),
                source_version,
            )
            continue

        plaintext = decrypt_content(envelope, keyring.keys[source_version].key)
        payload["ciphertext"] = encrypt_content(
            plaintext,
            active_key.key,
            salt=active_key.salt,
            key_version=active_version,
        )
        db.update_event_payload(event["id"], payload, tenant_id=tenant_id)
        rotated += 1
    return {"scanned": scanned, "rotated": rotated, "skipped_missing_keys": skipped_missing_keys}
