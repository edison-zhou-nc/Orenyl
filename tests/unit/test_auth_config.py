import socket

import pytest

from orenyl.auth import build_token_verifier_from_env
from orenyl.config import auth_required_for_runtime, dev_stdio_mode_enabled

_VALID_HS256_SECRET = "0123456789abcdef0123456789abcdef"


def _set_valid_hs256_env(monkeypatch) -> None:
    monkeypatch.setenv("ORENYL_OIDC_ISSUER", "https://issuer.example")
    monkeypatch.setenv("ORENYL_OIDC_ALLOWED_ALGS", "HS256")
    monkeypatch.setenv("ORENYL_OIDC_HS256_SECRET", _VALID_HS256_SECRET)
    monkeypatch.delenv("ORENYL_OIDC_JWKS_URL", raising=False)


def _set_valid_rs256_env(monkeypatch) -> None:
    monkeypatch.setenv("ORENYL_OIDC_ISSUER", "https://issuer.example")
    monkeypatch.setenv("ORENYL_OIDC_ALLOWED_ALGS", "RS256")
    monkeypatch.setenv("ORENYL_OIDC_JWKS_URL", "https://issuer.example/.well-known/jwks.json")
    monkeypatch.delenv("ORENYL_OIDC_HS256_SECRET", raising=False)


def test_build_token_verifier_requires_issuer_for_rs256(monkeypatch):
    monkeypatch.delenv("ORENYL_OIDC_ISSUER", raising=False)
    monkeypatch.setenv("ORENYL_OIDC_ALLOWED_ALGS", "RS256")
    monkeypatch.setenv("ORENYL_OIDC_JWKS_URL", "https://issuer.example/.well-known/jwks.json")
    with pytest.raises(RuntimeError, match="ORENYL_OIDC_ISSUER must be set"):
        build_token_verifier_from_env()


def test_build_token_verifier_requires_issuer_for_hs256(monkeypatch):
    monkeypatch.delenv("ORENYL_OIDC_ISSUER", raising=False)
    monkeypatch.delenv("ORENYL_OIDC_JWKS_URL", raising=False)
    monkeypatch.setenv("ORENYL_OIDC_ALLOWED_ALGS", "HS256")
    monkeypatch.setenv("ORENYL_OIDC_HS256_SECRET", _VALID_HS256_SECRET)
    with pytest.raises(RuntimeError, match="ORENYL_OIDC_ISSUER must be set"):
        build_token_verifier_from_env()


def test_build_token_verifier_rejects_non_integer_jwks_cache_ttl(monkeypatch):
    _set_valid_hs256_env(monkeypatch)
    monkeypatch.setenv("ORENYL_OIDC_JWKS_CACHE_TTL_SECONDS", "not-an-int")
    with pytest.raises(RuntimeError, match="ORENYL_OIDC_JWKS_CACHE_TTL_SECONDS must be an integer"):
        build_token_verifier_from_env()


def test_build_token_verifier_rejects_non_integer_clock_skew(monkeypatch):
    _set_valid_hs256_env(monkeypatch)
    monkeypatch.setenv("ORENYL_OIDC_CLOCK_SKEW_SECONDS", "not-an-int")
    with pytest.raises(RuntimeError, match="ORENYL_OIDC_CLOCK_SKEW_SECONDS must be an integer"):
        build_token_verifier_from_env()


def test_build_token_verifier_rejects_excessive_clock_skew(monkeypatch):
    _set_valid_hs256_env(monkeypatch)
    monkeypatch.setenv("ORENYL_OIDC_CLOCK_SKEW_SECONDS", "3600")
    with pytest.raises(RuntimeError, match="ORENYL_OIDC_CLOCK_SKEW_SECONDS must be <= 300"):
        build_token_verifier_from_env()


def test_dev_stdio_mode_disables_runtime_auth_requirement(monkeypatch):
    monkeypatch.setenv("ORENYL_TRANSPORT", "stdio")
    monkeypatch.setenv("ORENYL_ALLOW_STDIO_DEV", "1")

    assert dev_stdio_mode_enabled() is True
    assert auth_required_for_runtime() is False

    monkeypatch.setenv("ORENYL_TRANSPORT", "streamable-http")

    assert dev_stdio_mode_enabled() is False
    assert auth_required_for_runtime() is True


def test_build_token_verifier_rejects_mixed_hs256_and_rs256(monkeypatch):
    monkeypatch.setenv("ORENYL_OIDC_ISSUER", "https://issuer.example")
    monkeypatch.setenv("ORENYL_OIDC_JWKS_URL", "https://issuer.example/.well-known/jwks.json")
    monkeypatch.setenv("ORENYL_OIDC_ALLOWED_ALGS", "HS256,RS256")
    monkeypatch.setenv("ORENYL_OIDC_HS256_SECRET", _VALID_HS256_SECRET)

    with pytest.raises(RuntimeError, match="mixed_algorithms_not_allowed"):
        build_token_verifier_from_env()


def test_build_token_verifier_rejects_mixed_algorithms_without_both_key_sources(monkeypatch):
    monkeypatch.setenv("ORENYL_OIDC_ISSUER", "https://issuer.example")
    monkeypatch.setenv("ORENYL_OIDC_JWKS_URL", "https://issuer.example/.well-known/jwks.json")
    monkeypatch.setenv("ORENYL_OIDC_ALLOWED_ALGS", "HS256,RS256")
    monkeypatch.delenv("ORENYL_OIDC_HS256_SECRET", raising=False)

    with pytest.raises(RuntimeError, match="mixed_algorithms_not_allowed"):
        build_token_verifier_from_env()


def test_build_token_verifier_rejects_weak_hs256_secret(monkeypatch):
    monkeypatch.setenv("ORENYL_OIDC_ISSUER", "https://issuer.example")
    monkeypatch.setenv("ORENYL_OIDC_ALLOWED_ALGS", "HS256")
    monkeypatch.setenv("ORENYL_OIDC_HS256_SECRET", "short")
    monkeypatch.delenv("ORENYL_OIDC_JWKS_URL", raising=False)

    with pytest.raises(RuntimeError, match="hs256_secret_too_short"):
        build_token_verifier_from_env()


def test_build_token_verifier_accepts_valid_hs256_secret(monkeypatch):
    _set_valid_hs256_env(monkeypatch)

    verifier = build_token_verifier_from_env()

    assert verifier is not None
    assert verifier.hs256_secret == _VALID_HS256_SECRET


def test_build_token_verifier_requires_jwks_url_for_rs256(monkeypatch):
    monkeypatch.setenv("ORENYL_OIDC_ISSUER", "https://issuer.example")
    monkeypatch.setenv("ORENYL_OIDC_ALLOWED_ALGS", "RS256")
    monkeypatch.delenv("ORENYL_OIDC_JWKS_URL", raising=False)
    monkeypatch.delenv("ORENYL_OIDC_HS256_SECRET", raising=False)

    with pytest.raises(RuntimeError, match="jwks_url_required"):
        build_token_verifier_from_env()


def test_build_token_verifier_requires_https_jwks_url(monkeypatch):
    monkeypatch.setenv("ORENYL_OIDC_ISSUER", "https://issuer.example")
    monkeypatch.setenv("ORENYL_OIDC_ALLOWED_ALGS", "RS256")
    monkeypatch.setenv("ORENYL_OIDC_JWKS_URL", "http://issuer.example/.well-known/jwks.json")
    monkeypatch.delenv("ORENYL_OIDC_HS256_SECRET", raising=False)

    with pytest.raises(RuntimeError, match="jwks_url_must_use_https"):
        build_token_verifier_from_env()


def test_build_token_verifier_rejects_private_jwks_ip(monkeypatch):
    _set_valid_rs256_env(monkeypatch)
    monkeypatch.setenv("ORENYL_OIDC_JWKS_URL", "https://169.254.169.254/jwks")

    with pytest.raises(RuntimeError, match="jwks_url_private_ip_not_allowed"):
        build_token_verifier_from_env()


def test_build_token_verifier_rejects_private_jwks_dns_resolution(monkeypatch):
    _set_valid_rs256_env(monkeypatch)

    def _fake_getaddrinfo(*_args, **_kwargs):
        return [(socket.AF_INET, None, None, "", ("127.0.0.1", 0))]

    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo)

    with pytest.raises(RuntimeError, match="jwks_url_private_ip_not_allowed"):
        build_token_verifier_from_env()


def test_build_token_verifier_accepts_valid_jwks_url(monkeypatch):
    _set_valid_rs256_env(monkeypatch)

    verifier = build_token_verifier_from_env()

    assert verifier.jwks_url == "https://issuer.example/.well-known/jwks.json"
