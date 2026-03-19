"""Encryption interface hooks for optional secure payload handling."""

from __future__ import annotations

import base64
import logging
import os
from dataclasses import dataclass

from argon2.low_level import Type, hash_secret_raw
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from . import env_vars

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EncryptionKey:
    key: bytes
    salt: bytes


@dataclass(frozen=True)
class RuntimeKeyring:
    active_version: str
    keys: dict[str, EncryptionKey]


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


def _read_env(name: str) -> str:
    return os.environ.get(name, "").strip()


def _decode_salt(var_name: str) -> bytes:
    salt_b64 = _read_env(var_name)
    if salt_b64:
        return base64.b64decode(salt_b64)
    allow_insecure_dev_salt = _read_env(env_vars.ALLOW_INSECURE_DEV_SALT) == "1"
    if not allow_insecure_dev_salt:
        raise RuntimeError(f"{var_name} is required when passphrase is configured")
    logger.warning(
        "INSECURE DEV SALT ACTIVE: Using hardcoded fallback salt. "
        "This is NOT safe for production. Set %s to a base64-encoded random salt.",
        var_name,
    )
    return b"lore-default-salt!"


def resolve_runtime_keyring() -> RuntimeKeyring:
    active_version = _read_env(env_vars.ENCRYPTION_KEY_VERSION) or "v1"
    normalized = active_version.upper()
    passphrase_var = f"{env_vars.ENCRYPTION_PASSPHRASE_PREFIX}{normalized}"
    salt_var = f"{env_vars.ENCRYPTION_SALT_PREFIX}{normalized}"

    passphrase = _read_env(passphrase_var)
    if not passphrase:
        passphrase = _read_env(env_vars.ENCRYPTION_PASSPHRASE)
        salt = _decode_salt(env_vars.ENCRYPTION_SALT)
    else:
        salt = _decode_salt(salt_var)

    keys: dict[str, EncryptionKey] = {
        active_version: EncryptionKey(key=generate_key(passphrase, salt), salt=salt)
    }

    for env_name, env_value in os.environ.items():
        if not env_name.startswith(env_vars.ENCRYPTION_PASSPHRASE_PREFIX):
            continue
        if not env_value.strip():
            continue
        version_norm = env_name[len(env_vars.ENCRYPTION_PASSPHRASE_PREFIX) :]
        version = version_norm.lower()
        if version in keys:
            continue
        prev_salt = _decode_salt(f"{env_vars.ENCRYPTION_SALT_PREFIX}{version_norm}")
        keys[version] = EncryptionKey(key=generate_key(env_value, prev_salt), salt=prev_salt)

    return RuntimeKeyring(active_version=active_version, keys=keys)


def encrypt_content(plaintext: str, key: bytes, salt: bytes, key_version: str = "v1") -> dict:
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
        "key_version": key_version,
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
