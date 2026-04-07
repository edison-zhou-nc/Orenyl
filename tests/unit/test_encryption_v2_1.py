import base64

from orenyl.encryption import decrypt_content, encrypt_content, generate_key


def test_argon2id_key_derivation_and_envelope_metadata():
    salt = b"0123456789abcdef"
    key = generate_key("pw", salt)
    payload = encrypt_content("hello", key, salt=salt)

    assert payload["alg"] == "aes-256-gcm"
    assert payload["kdf"] == "argon2id"
    assert "salt" in payload
    base64.b64decode(payload["salt"])

    out = decrypt_content(payload, key)
    assert out == "hello"
