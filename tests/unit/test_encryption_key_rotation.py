import base64

import pytest

from orenyl.encryption import decrypt_content, encrypt_content, resolve_runtime_keyring


def test_resolve_runtime_keyring_uses_active_version_and_legacy_env(monkeypatch):
    monkeypatch.setenv("LORE_ENCRYPTION_KEY_VERSION", "v3")
    monkeypatch.setenv("LORE_ENCRYPTION_PASSPHRASE", "legacy-passphrase")
    monkeypatch.setenv(
        "LORE_ENCRYPTION_SALT", base64.b64encode(b"0123456789abcdef").decode("ascii")
    )

    keyring = resolve_runtime_keyring()
    assert keyring.active_version == "v3"
    assert "v3" in keyring.keys


def test_encrypt_payload_carries_key_version_and_round_trips(monkeypatch):
    monkeypatch.setenv("LORE_ENCRYPTION_KEY_VERSION", "v1")
    monkeypatch.setenv("LORE_ENCRYPTION_PASSPHRASE_V1", "0123456789abcdef")
    monkeypatch.setenv(
        "LORE_ENCRYPTION_SALT_V1", base64.b64encode(b"0123456789abcdef").decode("ascii")
    )

    keyring = resolve_runtime_keyring()
    key = keyring.keys[keyring.active_version]
    payload = encrypt_content("hello", key.key, salt=key.salt, key_version=keyring.active_version)

    assert payload["key_version"] == "v1"
    out = decrypt_content(payload, key.key)
    assert out == "hello"


def test_resolve_runtime_keyring_fails_without_required_salt(monkeypatch):
    monkeypatch.setenv("LORE_ENCRYPTION_KEY_VERSION", "v2")
    monkeypatch.setenv("LORE_ENCRYPTION_PASSPHRASE_V2", "fedcba9876543210")
    monkeypatch.delenv("LORE_ENCRYPTION_SALT_V2", raising=False)
    monkeypatch.delenv("LORE_ALLOW_INSECURE_DEV_SALT", raising=False)

    with pytest.raises(RuntimeError, match="LORE_ENCRYPTION_SALT_V2"):
        resolve_runtime_keyring()
