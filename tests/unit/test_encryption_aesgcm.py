import base64

import pytest
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from orenyl.encryption import decrypt_content, encrypt_content, generate_key, resolve_runtime_keyring


def _build_legacy_payload(plaintext: str, key: bytes, salt: bytes, key_version: str = "v1") -> dict:
    nonce = b"legacy-nonce"
    ciphertext = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), None)
    return {
        "alg": "aes-256-gcm",
        "kdf": "argon2id",
        "key_version": key_version,
        "salt": base64.b64encode(salt).decode("ascii"),
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
    }


def test_encrypt_decrypt_round_trip_aesgcm():
    salt = b"0123456789abcdef"
    key = generate_key("passphrase", salt)
    payload = encrypt_content("hello", key, salt=salt)
    assert payload["alg"] == "aes-256-gcm"
    assert payload["aad"] == "v1"
    assert decrypt_content(payload, key) == "hello"


def test_decrypt_rejects_wrong_key():
    salt = b"0123456789abcdef"
    key = generate_key("passphrase", salt)
    wrong_key = generate_key("wrong-passphrase", salt)
    payload = encrypt_content("hello", key, salt=salt)

    with pytest.raises(InvalidTag):
        decrypt_content(payload, wrong_key)


def test_decrypt_rejects_tampered_ciphertext():
    salt = b"0123456789abcdef"
    key = generate_key("passphrase", salt)
    payload = encrypt_content("hello", key, salt=salt)
    ciphertext = bytearray(base64.b64decode(payload["ciphertext"]))
    ciphertext[-1] ^= 0x01
    tampered_payload = dict(payload, ciphertext=base64.b64encode(ciphertext).decode("ascii"))

    with pytest.raises(InvalidTag):
        decrypt_content(tampered_payload, key)


def test_decrypt_rejects_missing_nonce():
    salt = b"0123456789abcdef"
    key = generate_key("passphrase", salt)
    payload = encrypt_content("hello", key, salt=salt)
    payload.pop("nonce")

    with pytest.raises(ValueError, match="malformed_ciphertext"):
        decrypt_content(payload, key)


def test_decrypt_rejects_malformed_base64_payload():
    salt = b"0123456789abcdef"
    key = generate_key("passphrase", salt)

    with pytest.raises(ValueError, match="malformed_ciphertext"):
        decrypt_content(
            {
                "alg": "aes-256-gcm",
                "kdf": "argon2id",
                "nonce": "!!!",
                "ciphertext": "!!!",
            },
            key,
        )


def test_decrypt_rejects_tampered_envelope_metadata():
    salt = b"0123456789abcdef"
    key = generate_key("passphrase", salt)
    payload = encrypt_content("hello", key, salt=salt, key_version="v1")
    tampered = dict(payload, key_version="v2")

    with pytest.raises(InvalidTag):
        decrypt_content(tampered, key)


def test_decrypt_supports_legacy_payload_without_aad():
    salt = b"0123456789abcdef"
    key = generate_key("passphrase", salt)
    payload = _build_legacy_payload("hello", key, salt=salt)

    assert "aad" not in payload
    assert decrypt_content(payload, key) == "hello"


def test_resolve_runtime_keyring_rejects_short_passphrase(monkeypatch):
    monkeypatch.setenv("ORENYL_ENCRYPTION_PASSPHRASE", "short")
    monkeypatch.setenv("ORENYL_ENCRYPTION_SALT", base64.b64encode(b"0123456789abcdef").decode("ascii"))

    with pytest.raises(RuntimeError, match="passphrase_too_short"):
        resolve_runtime_keyring()


def test_resolve_runtime_keyring_accepts_16_char_passphrase(monkeypatch):
    monkeypatch.setenv("ORENYL_ENCRYPTION_PASSPHRASE", "0123456789abcdef")
    monkeypatch.setenv("ORENYL_ENCRYPTION_SALT", base64.b64encode(b"0123456789abcdef").decode("ascii"))

    keyring = resolve_runtime_keyring()

    assert keyring.active_version == "v1"
    assert keyring.keys["v1"].key
