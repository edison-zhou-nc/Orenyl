import contextlib

import pytest

from lore.tenant import (
    TenantContext,
    get_current_tenant_context,
    reset_current_tenant_context,
    resolve_tenant_context,
    set_current_tenant_context,
)


@contextlib.contextmanager
def _env(name: str, value: str | None):
    import os

    previous = os.environ.get(name)
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = previous


def test_resolve_tenant_context_prefers_token_claims():
    claims = {"sub": "user-1", "tenant_id": "tenant-a"}
    with _env("LORE_ENABLE_MULTI_TENANT", "1"):
        ctx = resolve_tenant_context(claims=claims, args={"agent_id": "agent-1", "session_id": "s1"})
    assert ctx.tenant_id == "tenant-a"
    assert ctx.user_id == "user-1"
    assert ctx.agent_id == "agent-1"
    assert ctx.session_id == "s1"


def test_resolve_tenant_context_defaults_when_multi_tenant_disabled():
    with _env("LORE_ENABLE_MULTI_TENANT", "0"):
        ctx = resolve_tenant_context(claims={"sub": "user-2"}, args={})
    assert ctx.tenant_id == "default"
    assert ctx.user_id == "user-2"


def test_resolve_tenant_context_requires_tenant_when_enabled():
    with _env("LORE_ENABLE_MULTI_TENANT", "1"):
        with pytest.raises(PermissionError, match="tenant_scope_violation"):
            resolve_tenant_context(claims={"sub": "user-3"}, args={})


def test_tenant_context_contextvar_round_trip():
    assert get_current_tenant_context() is None
    context = TenantContext(tenant_id="tenant-z", user_id="user-z", agent_id="", session_id="")
    token = set_current_tenant_context(context)
    assert get_current_tenant_context() == context
    reset_current_tenant_context(token)
    assert get_current_tenant_context() is None
