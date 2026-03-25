import base64

import pytest

from lore.encryption import decrypt_content, encrypt_content, generate_key


def test_encrypt_decrypt_round_trip_aesgcm():
    salt = b"0123456789abcdef"
    key = generate_key("passphrase", salt)
    payload = encrypt_content("hello", key, salt=salt)
    assert payload["alg"] == "aes-256-gcm"
    assert decrypt_content(payload, key) == "hello"


def test_decrypt_rejects_wrong_key():
    salt = b"0123456789abcdef"
    key = generate_key("passphrase", salt)
    wrong_key = generate_key("wrong-passphrase", salt)
    payload = encrypt_content("hello", key, salt=salt)

    with pytest.raises(Exception):
        decrypt_content(payload, wrong_key)


def test_decrypt_rejects_tampered_ciphertext():
    salt = b"0123456789abcdef"
    key = generate_key("passphrase", salt)
    payload = encrypt_content("hello", key, salt=salt)
    ciphertext = bytearray(base64.b64decode(payload["ciphertext"]))
    ciphertext[-1] ^= 0x01
    tampered_payload = dict(payload, ciphertext=base64.b64encode(ciphertext).decode("ascii"))

    with pytest.raises(Exception):
        decrypt_content(tampered_payload, key)


def test_decrypt_rejects_missing_nonce():
    salt = b"0123456789abcdef"
    key = generate_key("passphrase", salt)
    payload = encrypt_content("hello", key, salt=salt)
    payload.pop("nonce")

    with pytest.raises(Exception):
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
