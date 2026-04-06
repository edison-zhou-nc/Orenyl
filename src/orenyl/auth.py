"""Authentication and authorization helpers for orenyl."""

from __future__ import annotations

import asyncio
import ipaddress
import json
import logging
import os
import socket
import threading
import time
from urllib.parse import urlparse
from collections.abc import Iterable

import httpx
import jwt
from jwt import InvalidTokenError
from jwt.algorithms import RSAAlgorithm
from mcp.server.auth.provider import AccessToken

from . import env_vars

logger = logging.getLogger(__name__)
ACTION_SCOPE_REQUIREMENTS = {
    "store_event": "memory:write",
    "retrieve_context_pack": "memory:read",
    "delete_and_recompute": "memory:delete",
    "audit_trace": "memory:read",
    "list_events": "memory:read",
    "export_domain": "memory:export",
    "erase_subject_data": "memory:delete",
    "export_subject_data": "memory:export",
    "record_consent": "memory:write",
    "generate_processing_record": "memory:export",
    "audit_anomaly_scan": "memory:read",
    "create_snapshot": "memory:write",
    "verify_snapshot": "memory:read",
    "restore_snapshot": "memory:delete",
}
RESTRICTED_EXPORT_SCOPE = "memory:export:restricted"


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
        self.allowed_algorithms = tuple(
            allowed_algorithms or (("RS256",) if jwks_url else ("HS256",))
        )
        self.jwks_cache_ttl_seconds = jwks_cache_ttl_seconds
        self.clock_skew_seconds = clock_skew_seconds
        self._jwks_cache: dict | None = None
        self._jwks_cache_expires_at = 0
        self._jwks_lock: asyncio.Lock | None = None
        self._jwks_lock_loop: asyncio.AbstractEventLoop | None = None
        self._jwks_lock_init_guard = threading.Lock()

    def _get_jwks_lock(self) -> asyncio.Lock:
        current_loop = asyncio.get_running_loop()
        with self._jwks_lock_init_guard:
            if self._jwks_lock is None or self._jwks_lock_loop is not current_loop:
                self._jwks_lock = asyncio.Lock()
                self._jwks_lock_loop = current_loop
        return self._jwks_lock

    async def verify_token(self, token: str) -> AccessToken | None:
        if not token:
            return None

        try:
            header = jwt.get_unverified_header(token)
            algorithm = str(header.get("alg", "")).upper()
            if algorithm not in self.allowed_algorithms:
                return None
            key = await self._resolve_signing_key(header, algorithm)
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
        tenant_id = _extract_tenant_id(claims)
        if not client_id:
            return None

        return AccessToken(
            token=token,
            client_id=client_id,
            scopes=scopes,
            expires_at=expires_at,
            resource=tenant_id or None,
        )

    async def _resolve_signing_key(self, header: dict, algorithm: str):
        if algorithm.startswith("HS"):
            return self.hs256_secret if self.hs256_secret else None
        if algorithm.startswith("RS"):
            key = await self._get_jwk_for_header(header)
            if key is None:
                return None
            return RSAAlgorithm.from_jwk(json.dumps(key))
        return None

    async def _get_jwk_for_header(self, header: dict) -> dict | None:
        jwks = await self._get_jwks()
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

    async def _get_jwks(self) -> dict:
        now = int(time.time())
        # Fast-path assumes a single event loop in normal server operation.
        if self._jwks_cache is not None and now < self._jwks_cache_expires_at:
            return self._jwks_cache
        async with self._get_jwks_lock():
            now = int(time.time())
            if self._jwks_cache is not None and now < self._jwks_cache_expires_at:
                return self._jwks_cache
            jwks = await self._fetch_jwks()
            if not isinstance(jwks, dict):
                jwks = {}
            self._jwks_cache = jwks
            cache_ttl = max(1, int(self.jwks_cache_ttl_seconds))
            if not jwks.get("keys"):
                cache_ttl = min(30, cache_ttl)
            self._jwks_cache_expires_at = now + cache_ttl
            return jwks

    async def _fetch_jwks(self) -> dict:
        if not self.jwks_url:
            return {}
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(self.jwks_url)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            logger.warning(
                "jwks_fetch_failed url=%s status=%s error=%s",
                self.jwks_url,
                status_code,
                exc,
            )
            return {}
        # Parse errors are handled separately to keep fetch diagnostics explicit.
        try:
            payload = response.json()
        except json.JSONDecodeError:
            logger.warning("jwks_parse_failed url=%s", self.jwks_url)
            return {}
        return payload if isinstance(payload, dict) else {}


def _extract_scopes(claims: dict) -> list[str]:
    raw_scope = claims.get("scope")
    if isinstance(raw_scope, str):
        return [s for s in raw_scope.split() if s]

    scp = claims.get("scp")
    if isinstance(scp, list):
        return [str(s) for s in scp if s]

    return []


def _extract_tenant_id(claims: dict) -> str:
    for key in ("tenant_id", "tenant", "tid", "organization_id", "org_id"):
        value = claims.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def extract_auth_token(arguments: dict) -> str:
    token = arguments.pop("_auth_token", "")
    return token if isinstance(token, str) else ""


def _parse_int_env(
    name: str,
    default: int,
    *,
    min_value: int | None = None,
    max_value: int | None = None,
) -> int:
    raw = os.environ.get(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc
    if min_value is not None and value < min_value:
        raise RuntimeError(f"{name} must be >= {min_value}")
    if max_value is not None and value > max_value:
        raise RuntimeError(f"{name} must be <= {max_value}")
    return value


def _reject_private_ip(host: str, raw_url: str) -> None:
    ip = ipaddress.ip_address(host)
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        raise RuntimeError(
            f"jwks_url_private_ip_not_allowed: {env_vars.OIDC_JWKS_URL} "
            f"must not resolve to private IP ({host})"
        )


def _validate_jwks_url(jwks_url: str) -> None:
    parsed = urlparse(jwks_url)
    if parsed.scheme != "https":
        raise RuntimeError(
            f"jwks_url_must_use_https: {env_vars.OIDC_JWKS_URL} must use "
            f"https:// scheme, got {parsed.scheme or '<missing>'}://"
        )
    if not parsed.hostname:
        raise RuntimeError(
            f"jwks_url_must_use_https: {env_vars.OIDC_JWKS_URL} must include a host"
        )

    try:
        _reject_private_ip(parsed.hostname, jwks_url)
        return
    except ValueError:
        pass

    try:
        resolved = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror:
        return

    for _, _, _, _, addr in resolved:
        host = addr[0]
        if not isinstance(host, str):
            continue
        try:
            _reject_private_ip(host, jwks_url)
        except ValueError:
            continue


def build_token_verifier_from_env() -> OIDCTokenVerifier:
    jwks_url = os.environ.get(env_vars.OIDC_JWKS_URL, "").strip()
    allowed_algorithms_raw = os.environ.get(env_vars.OIDC_ALLOWED_ALGS, "RS256")
    allowed_algorithms = tuple(
        alg.strip().upper() for alg in allowed_algorithms_raw.split(",") if alg.strip()
    )
    normalized_algorithms = allowed_algorithms or ("RS256",)
    issuer = os.environ.get(env_vars.OIDC_ISSUER, "").strip()
    hs256_secret = os.environ.get(env_vars.OIDC_HS256_SECRET, "")
    if "HS256" in normalized_algorithms and "RS256" in normalized_algorithms:
        raise RuntimeError(
            "mixed_algorithms_not_allowed: configure either HS256 or RS256 in "
            f"{env_vars.OIDC_ALLOWED_ALGS}, not both"
        )
    if "HS256" in normalized_algorithms and len(hs256_secret) < 32:
        raise RuntimeError(
            f"hs256_secret_too_short: {env_vars.OIDC_HS256_SECRET} must be at least "
            "32 bytes when HS256 is configured"
        )
    if "RS256" in normalized_algorithms and not jwks_url:
        raise RuntimeError(
            f"jwks_url_required: {env_vars.OIDC_JWKS_URL} must be set when "
            "RS256 is in the allowed algorithms"
        )
    if jwks_url:
        _validate_jwks_url(jwks_url)
    if not issuer:
        raise RuntimeError(f"{env_vars.OIDC_ISSUER} must be set when RS256/JWKS is enabled")
    return OIDCTokenVerifier(
        issuer=issuer,
        audience=os.environ.get(env_vars.OIDC_AUDIENCE, "orenyl"),
        hs256_secret=hs256_secret,
        jwks_url=jwks_url,
        allowed_algorithms=normalized_algorithms,
        jwks_cache_ttl_seconds=_parse_int_env(env_vars.OIDC_JWKS_CACHE_TTL_SECONDS, 300),
        clock_skew_seconds=_parse_int_env(
            env_vars.OIDC_CLOCK_SKEW_SECONDS,
            30,
            min_value=0,
            max_value=300,
        ),
    )


def all_authorization_scopes() -> list[str]:
    return sorted({*ACTION_SCOPE_REQUIREMENTS.values(), RESTRICTED_EXPORT_SCOPE})


def authorize_action(
    scopes: set[str] | Iterable[str],
    action: str,
    restricted: bool = False,
) -> None:
    scope_set = set(scopes)
    required = ACTION_SCOPE_REQUIREMENTS.get(action)

    if required and required not in scope_set:
        raise PermissionError(f"missing_scope:{required}")

    if action == "export_domain" and restricted and RESTRICTED_EXPORT_SCOPE not in scope_set:
        raise PermissionError(f"missing_scope:{RESTRICTED_EXPORT_SCOPE}")
