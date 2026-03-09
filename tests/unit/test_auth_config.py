import pytest

from lore.auth import build_token_verifier_from_env


def test_build_token_verifier_requires_issuer_for_rs256(monkeypatch):
    monkeypatch.delenv("LORE_OIDC_ISSUER", raising=False)
    monkeypatch.delenv("LORE_OIDC_JWKS_URL", raising=False)
    monkeypatch.setenv("LORE_OIDC_ALLOWED_ALGS", "RS256")
    with pytest.raises(RuntimeError, match="LORE_OIDC_ISSUER must be set"):
        build_token_verifier_from_env()


def test_build_token_verifier_allows_hs256_without_issuer(monkeypatch):
    monkeypatch.delenv("LORE_OIDC_ISSUER", raising=False)
    monkeypatch.delenv("LORE_OIDC_JWKS_URL", raising=False)
    monkeypatch.setenv("LORE_OIDC_ALLOWED_ALGS", "HS256")
    verifier = build_token_verifier_from_env()
    assert verifier.issuer == "https://issuer.example"


def test_build_token_verifier_rejects_non_integer_jwks_cache_ttl(monkeypatch):
    monkeypatch.delenv("LORE_OIDC_ISSUER", raising=False)
    monkeypatch.delenv("LORE_OIDC_JWKS_URL", raising=False)
    monkeypatch.setenv("LORE_OIDC_ALLOWED_ALGS", "HS256")
    monkeypatch.setenv("LORE_OIDC_JWKS_CACHE_TTL_SECONDS", "not-an-int")
    with pytest.raises(RuntimeError, match="LORE_OIDC_JWKS_CACHE_TTL_SECONDS must be an integer"):
        build_token_verifier_from_env()


def test_build_token_verifier_rejects_non_integer_clock_skew(monkeypatch):
    monkeypatch.delenv("LORE_OIDC_ISSUER", raising=False)
    monkeypatch.delenv("LORE_OIDC_JWKS_URL", raising=False)
    monkeypatch.setenv("LORE_OIDC_ALLOWED_ALGS", "HS256")
    monkeypatch.setenv("LORE_OIDC_CLOCK_SKEW_SECONDS", "not-an-int")
    with pytest.raises(RuntimeError, match="LORE_OIDC_CLOCK_SKEW_SECONDS must be an integer"):
        build_token_verifier_from_env()


def test_build_token_verifier_rejects_excessive_clock_skew(monkeypatch):
    monkeypatch.delenv("LORE_OIDC_ISSUER", raising=False)
    monkeypatch.delenv("LORE_OIDC_JWKS_URL", raising=False)
    monkeypatch.setenv("LORE_OIDC_ALLOWED_ALGS", "HS256")
    monkeypatch.setenv("LORE_OIDC_CLOCK_SKEW_SECONDS", "3600")
    with pytest.raises(RuntimeError, match="LORE_OIDC_CLOCK_SKEW_SECONDS must be <= 300"):
        build_token_verifier_from_env()
