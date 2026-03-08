import asyncio
import json
import time

import jwt
from jwt.algorithms import RSAAlgorithm
from cryptography.hazmat.primitives.asymmetric import rsa

from lore.auth import OIDCTokenVerifier

_TEST_SECRET = "0123456789abcdef0123456789abcdef"


def _make_token(secret: str, iss: str = "https://issuer.example", aud: str = "lore", scopes=None):
    now = int(time.time())
    payload = {
        "sub": "user-1",
        "iss": iss,
        "aud": aud,
        "iat": now,
        "exp": now + 300,
        "scope": " ".join(scopes or ["memory:read"]),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def _make_rsa_keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    return private_key, public_key


def _make_rs256_token(private_key, kid: str, iss: str = "https://issuer.example", aud: str = "lore", scopes=None):
    now = int(time.time())
    payload = {
        "sub": "user-1",
        "iss": iss,
        "aud": aud,
        "iat": now,
        "exp": now + 300,
        "scope": " ".join(scopes or ["memory:read"]),
    }
    return jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": kid})


def test_verify_token_rejects_wrong_issuer():
    verifier = OIDCTokenVerifier(
        issuer="https://issuer.example",
        audience="lore",
        hs256_secret=_TEST_SECRET,
    )
    token = _make_token(_TEST_SECRET, iss="https://bad-issuer.example")
    assert asyncio.run(verifier.verify_token(token)) is None


def test_verify_token_rejects_wrong_audience():
    verifier = OIDCTokenVerifier(
        issuer="https://issuer.example",
        audience="lore",
        hs256_secret=_TEST_SECRET,
    )
    token = _make_token(_TEST_SECRET, aud="other")
    assert asyncio.run(verifier.verify_token(token)) is None


def test_verify_token_accepts_valid_token():
    verifier = OIDCTokenVerifier(
        issuer="https://issuer.example",
        audience="lore",
        hs256_secret=_TEST_SECRET,
    )
    token = _make_token(_TEST_SECRET, scopes=["memory:read", "memory:delete"])
    access = asyncio.run(verifier.verify_token(token))
    assert access is not None
    assert access.client_id == "user-1"
    assert set(access.scopes) == {"memory:read", "memory:delete"}


def test_verify_token_accepts_valid_rs256_token_with_jwks():
    private_key, public_key = _make_rsa_keypair()
    kid = "kid-1"
    jwk = json.loads(RSAAlgorithm.to_jwk(public_key))
    jwk["kid"] = kid
    jwk["use"] = "sig"
    verifier = OIDCTokenVerifier(
        issuer="https://issuer.example",
        audience="lore",
        hs256_secret="",
        jwks_url="https://issuer.example/.well-known/jwks.json",
        allowed_algorithms=("RS256",),
    )
    verifier._fetch_jwks = lambda: {"keys": [jwk]}
    token = _make_rs256_token(private_key, kid=kid, scopes=["memory:read", "memory:delete"])

    access = asyncio.run(verifier.verify_token(token))

    assert access is not None
    assert access.client_id == "user-1"
    assert set(access.scopes) == {"memory:read", "memory:delete"}


def test_verify_token_rejects_rs256_token_with_unknown_kid():
    private_key, public_key = _make_rsa_keypair()
    jwk = json.loads(RSAAlgorithm.to_jwk(public_key))
    jwk["kid"] = "some-other-kid"
    verifier = OIDCTokenVerifier(
        issuer="https://issuer.example",
        audience="lore",
        hs256_secret="",
        jwks_url="https://issuer.example/.well-known/jwks.json",
        allowed_algorithms=("RS256",),
    )
    verifier._fetch_jwks = lambda: {"keys": [jwk]}
    token = _make_rs256_token(private_key, kid="missing-kid")

    assert asyncio.run(verifier.verify_token(token)) is None

