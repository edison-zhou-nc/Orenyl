import pytest

from lore.auth import build_token_verifier_from_env
from lore.config import auth_required_for_runtime, dev_stdio_mode_enabled


def test_build_token_verifier_requires_issuer_for_rs256(monkeypatch):
    monkeypatch.delenv("LORE_OIDC_ISSUER", raising=False)
    monkeypatch.delenv("LORE_OIDC_JWKS_URL", raising=False)
    monkeypatch.setenv("LORE_OIDC_ALLOWED_ALGS", "RS256")
    with pytest.raises(RuntimeError, match="LORE_OIDC_ISSUER must be set"):
        build_token_verifier_from_env()


def test_build_token_verifier_requires_issuer_for_hs256(monkeypatch):
    monkeypatch.delenv("LORE_OIDC_ISSUER", raising=False)
    monkeypatch.delenv("LORE_OIDC_JWKS_URL", raising=False)
    monkeypatch.setenv("LORE_OIDC_ALLOWED_ALGS", "HS256")
    with pytest.raises(RuntimeError, match="LORE_OIDC_ISSUER must be set"):
        build_token_verifier_from_env()


def test_build_token_verifier_rejects_non_integer_jwks_cache_ttl(monkeypatch):
    monkeypatch.setenv("LORE_OIDC_ISSUER", "https://issuer.example")
    monkeypatch.delenv("LORE_OIDC_JWKS_URL", raising=False)
    monkeypatch.setenv("LORE_OIDC_ALLOWED_ALGS", "HS256")
    monkeypatch.setenv("LORE_OIDC_JWKS_CACHE_TTL_SECONDS", "not-an-int")
    with pytest.raises(RuntimeError, match="LORE_OIDC_JWKS_CACHE_TTL_SECONDS must be an integer"):
        build_token_verifier_from_env()


def test_build_token_verifier_rejects_non_integer_clock_skew(monkeypatch):
    monkeypatch.setenv("LORE_OIDC_ISSUER", "https://issuer.example")
    monkeypatch.delenv("LORE_OIDC_JWKS_URL", raising=False)
    monkeypatch.setenv("LORE_OIDC_ALLOWED_ALGS", "HS256")
    monkeypatch.setenv("LORE_OIDC_CLOCK_SKEW_SECONDS", "not-an-int")
    with pytest.raises(RuntimeError, match="LORE_OIDC_CLOCK_SKEW_SECONDS must be an integer"):
        build_token_verifier_from_env()


def test_build_token_verifier_rejects_excessive_clock_skew(monkeypatch):
    monkeypatch.setenv("LORE_OIDC_ISSUER", "https://issuer.example")
    monkeypatch.delenv("LORE_OIDC_JWKS_URL", raising=False)
    monkeypatch.setenv("LORE_OIDC_ALLOWED_ALGS", "HS256")
    monkeypatch.setenv("LORE_OIDC_CLOCK_SKEW_SECONDS", "3600")
    with pytest.raises(RuntimeError, match="LORE_OIDC_CLOCK_SKEW_SECONDS must be <= 300"):
        build_token_verifier_from_env()


def test_dev_stdio_mode_disables_runtime_auth_requirement(monkeypatch):
    monkeypatch.setenv("LORE_TRANSPORT", "stdio")
    monkeypatch.setenv("LORE_ALLOW_STDIO_DEV", "1")

    assert dev_stdio_mode_enabled() is True
    assert auth_required_for_runtime() is False

    monkeypatch.setenv("LORE_TRANSPORT", "streamable-http")

    assert dev_stdio_mode_enabled() is False
    assert auth_required_for_runtime() is True


def test_build_token_verifier_warns_on_mixed_hs256_and_rs256(caplog, monkeypatch):
    monkeypatch.setenv("LORE_OIDC_ISSUER", "https://issuer.example")
    monkeypatch.setenv("LORE_OIDC_JWKS_URL", "https://issuer.example/.well-known/jwks.json")
    monkeypatch.setenv("LORE_OIDC_ALLOWED_ALGS", "HS256,RS256")
    monkeypatch.setenv("LORE_OIDC_HS256_SECRET", "super-secret")

    build_token_verifier_from_env()

    assert any("mixed_hs256_rs256" in record.message for record in caplog.records)


def test_build_token_verifier_warns_on_mixed_algorithms_without_both_key_sources(
    caplog, monkeypatch
):
    monkeypatch.setenv("LORE_OIDC_ISSUER", "https://issuer.example")
    monkeypatch.setenv("LORE_OIDC_JWKS_URL", "https://issuer.example/.well-known/jwks.json")
    monkeypatch.setenv("LORE_OIDC_ALLOWED_ALGS", "HS256,RS256")
    monkeypatch.delenv("LORE_OIDC_HS256_SECRET", raising=False)

    build_token_verifier_from_env()

    assert any("mixed_hs256_rs256" in record.message for record in caplog.records)
