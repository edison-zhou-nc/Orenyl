from lore.encryption import decrypt_content, encrypt_content, generate_key


def test_encrypt_decrypt_round_trip_aesgcm():
    salt = b"0123456789abcdef"
    key = generate_key("passphrase", salt)
    payload = encrypt_content("hello", key, salt=salt)
    assert payload["alg"] == "aes-256-gcm"
    assert decrypt_content(payload, key) == "hello"
