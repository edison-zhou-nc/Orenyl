"""Tenant context helpers for request scoping."""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Any

from .config import multi_tenant_enabled


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str
    user_id: str
    agent_id: str = ""
    session_id: str = ""


_CURRENT_TENANT_CONTEXT: ContextVar[TenantContext | None] = ContextVar(
    "lore_current_tenant_context",
    default=None,
)


def set_current_tenant_context(context: TenantContext) -> Token:
    return _CURRENT_TENANT_CONTEXT.set(context)


def reset_current_tenant_context(token: Token) -> None:
    _CURRENT_TENANT_CONTEXT.reset(token)


def get_current_tenant_context() -> TenantContext | None:
    return _CURRENT_TENANT_CONTEXT.get()


def resolve_tenant_context(
    claims: dict[str, Any] | None = None,
    args: dict[str, Any] | None = None,
) -> TenantContext:
    claim_data = claims or {}
    arg_data = args or {}

    user_id = str(claim_data.get("sub", "")).strip()
    tenant_claim = str(
        claim_data.get("tenant_id")
        or claim_data.get("tenant")
        or claim_data.get("tid")
        or ""
    ).strip()
    tenant_arg = str(arg_data.get("tenant_id", "")).strip()
    if not multi_tenant_enabled():
        tenant_id = "default"
    else:
        if tenant_claim and tenant_arg and tenant_claim != tenant_arg:
            raise PermissionError("tenant_scope_violation")
        tenant_id = tenant_claim or tenant_arg
        if not tenant_id:
            raise PermissionError("tenant_scope_violation")

    return TenantContext(
        tenant_id=tenant_id,
        user_id=user_id,
        agent_id=str(arg_data.get("agent_id", "")).strip(),
        session_id=str(arg_data.get("session_id", "")).strip(),
    )
