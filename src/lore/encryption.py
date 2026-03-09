"""Encryption interface hooks for optional secure payload handling."""

from __future__ import annotations

import base64
import os
from argon2.low_level import Type, hash_secret_raw
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def generate_key(passphrase: str, salt: bytes) -> bytes:
    return hash_secret_raw(
        secret=passphrase.encode("utf-8"),
        salt=salt,
        time_cost=3,
        memory_cost=64 * 1024,
        parallelism=1,
        hash_len=32,
        type=Type.ID,
    )


def encrypt_content(plaintext: str, key: bytes, salt: bytes) -> dict:
    aesgcm = AESGCM(key)
    if not salt:
        raise ValueError("missing_salt")
    if len(salt) < 8:
        raise ValueError("salt_too_short")
    nonce = os.urandom(12)
    
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return {
        "alg": "aes-256-gcm",
        "kdf": "argon2id",
        "salt": base64.b64encode(salt).decode("ascii"),
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
    }


def decrypt_content(payload: dict, key: bytes) -> str:
    if payload.get("alg") != "aes-256-gcm":
        raise ValueError("unsupported_algorithm")
    if payload.get("kdf") != "argon2id":
        raise ValueError("unsupported_kdf")
    nonce = base64.b64decode(payload["nonce"])
    ciphertext = base64.b64decode(payload["ciphertext"])
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")
