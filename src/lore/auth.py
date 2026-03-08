"""Authentication and authorization helpers for Lore."""

from __future__ import annotations

import json
import os
import time
from typing import Iterable
from urllib.request import urlopen

import jwt
from jwt.algorithms import RSAAlgorithm
from jwt import InvalidTokenError
from mcp.server.auth.provider import AccessToken


class OIDCTokenVerifier:
    def __init__(
        self,
        issuer: str,
        audience: str,
        hs256_secret: str,
        jwks_url: str = "",
        allowed_algorithms: tuple[str, ...] | None = None,
        jwks_cache_ttl_seconds: int = 300,
        clock_skew_seconds: int = 30,
    ):
        self.issuer = issuer
        self.audience = audience
        self.hs256_secret = hs256_secret
        self.jwks_url = jwks_url
        self.allowed_algorithms = tuple(allowed_algorithms or (("RS256",) if jwks_url else ("HS256",)))
        self.jwks_cache_ttl_seconds = jwks_cache_ttl_seconds
        self.clock_skew_seconds = clock_skew_seconds
        self._jwks_cache: dict | None = None
        self._jwks_cache_expires_at = 0

    async def verify_token(self, token: str) -> AccessToken | None:
        if not token:
            return None

        try:
            header = jwt.get_unverified_header(token)
            algorithm = str(header.get("alg", "")).upper()
            if algorithm not in self.allowed_algorithms:
                return None
            key = self._resolve_signing_key(header, algorithm)
            if key is None:
                return None
            claims = jwt.decode(
                token,
                key,
                algorithms=[algorithm],
                issuer=self.issuer,
                audience=self.audience,
                leeway=self.clock_skew_seconds,
                options={"require": ["exp", "iat", "iss", "aud", "sub"]},
            )
        except InvalidTokenError:
            return None

        scopes = _extract_scopes(claims)
        expires_at = int(claims["exp"]) if "exp" in claims else None
        client_id = str(claims.get("sub", ""))
        if not client_id:
            return None
        if expires_at is not None and expires_at < int(time.time()):
            return None

        return AccessToken(
            token=token,
            client_id=client_id,
            scopes=scopes,
            expires_at=expires_at,
        )

    def _resolve_signing_key(self, header: dict, algorithm: str):
        if algorithm.startswith("HS"):
            return self.hs256_secret if self.hs256_secret else None
        if algorithm.startswith("RS"):
            key = self._get_jwk_for_header(header)
            if key is None:
                return None
            return RSAAlgorithm.from_jwk(json.dumps(key))
        return None

    def _get_jwk_for_header(self, header: dict) -> dict | None:
        jwks = self._get_jwks()
        keys = jwks.get("keys", [])
        if not isinstance(keys, list) or not keys:
            return None
        kid = header.get("kid")
        if kid:
            for key in keys:
                if isinstance(key, dict) and key.get("kid") == kid:
                    return key
            return None
        if len(keys) == 1 and isinstance(keys[0], dict):
            return keys[0]
        return None

    def _get_jwks(self) -> dict:
        now = int(time.time())
        if self._jwks_cache is not None and now < self._jwks_cache_expires_at:
            return self._jwks_cache
        jwks = self._fetch_jwks()
        if not isinstance(jwks, dict):
            jwks = {}
        self._jwks_cache = jwks
        self._jwks_cache_expires_at = now + max(1, int(self.jwks_cache_ttl_seconds))
        return jwks

    def _fetch_jwks(self) -> dict:
        if not self.jwks_url:
            return {}
        with urlopen(self.jwks_url, timeout=5) as response:
            payload = response.read().decode("utf-8")
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return {}


def _extract_scopes(claims: dict) -> list[str]:
    raw_scope = claims.get("scope")
    if isinstance(raw_scope, str):
        return [s for s in raw_scope.split() if s]

    scp = claims.get("scp")
    if isinstance(scp, list):
        return [str(s) for s in scp if s]

    return []


def extract_auth_token(arguments: dict) -> str:
    token = arguments.pop("_auth_token", "")
    return token if isinstance(token, str) else ""


def build_token_verifier_from_env() -> OIDCTokenVerifier:
    allowed_algorithms_raw = os.environ.get("LORE_OIDC_ALLOWED_ALGS", "RS256")
    allowed_algorithms = tuple(
        alg.strip().upper() for alg in allowed_algorithms_raw.split(",") if alg.strip()
    )
    return OIDCTokenVerifier(
        issuer=os.environ.get("LORE_OIDC_ISSUER", "https://issuer.example"),
        audience=os.environ.get("LORE_OIDC_AUDIENCE", "lore"),
        hs256_secret=os.environ.get("LORE_OIDC_HS256_SECRET", ""),
        jwks_url=os.environ.get("LORE_OIDC_JWKS_URL", ""),
        allowed_algorithms=allowed_algorithms or ("RS256",),
        jwks_cache_ttl_seconds=int(os.environ.get("LORE_OIDC_JWKS_CACHE_TTL_SECONDS", "300")),
        clock_skew_seconds=int(os.environ.get("LORE_OIDC_CLOCK_SKEW_SECONDS", "30")),
    )


def authorize_action(scopes: set[str] | Iterable[str], action: str, restricted: bool = False) -> None:
    scope_set = set(scopes)
    required = {
        "store_event": "memory:write",
        "retrieve_context_pack": "memory:read",
        "delete_and_recompute": "memory:delete",
        "audit_trace": "memory:read",
        "list_events": "memory:read",
        "export_domain": "memory:export",
    }.get(action)

    if required and required not in scope_set:
        raise PermissionError(f"missing_scope:{required}")

    if action == "export_domain" and restricted and "memory:export:restricted" not in scope_set:
        raise PermissionError("missing_scope:memory:export:restricted")
