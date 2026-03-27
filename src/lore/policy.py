"""Agent/domain policy enforcement."""

from __future__ import annotations

import logging
import os

from . import env_vars
from .config import multi_tenant_enabled
from .db import Database
from .models import now_iso

logger = logging.getLogger(__name__)


class PolicyEngine:
    def __init__(self, db: Database, shadow_mode: bool = False):
        self.db = db
        self.shadow_mode = shadow_mode

    def can_read_domain(self, tenant_id: str, agent_id: str, domain: str) -> bool:
        return self.db.has_agent_permission(
            tenant_id=tenant_id,
            agent_id=agent_id,
            domain=domain,
            action="read",
            at_ts=now_iso(),
        )

    def can_write_domain(self, tenant_id: str, agent_id: str, domain: str) -> bool:
        return self.db.has_agent_permission(
            tenant_id=tenant_id,
            agent_id=agent_id,
            domain=domain,
            action="write",
            at_ts=now_iso(),
        )

    def can_delegate_read(
        self,
        tenant_id: str,
        agent_id: str,
        domain: str,
        now: str | None = None,
    ) -> bool:
        return self.db.has_delegation_grant(
            tenant_id=tenant_id,
            grantee_agent_id=agent_id,
            domain=domain,
            action="read",
            at_ts=now or now_iso(),
        )

    def enforce_read_domain(self, tenant_id: str, agent_id: str, domain: str) -> bool:
        if self.can_read_domain(tenant_id, agent_id, domain):
            return True
        if self.can_delegate_read(tenant_id, agent_id, domain):
            return True
        if self.shadow_mode:
            logger.info(
                "policy_shadow_deny action=read tenant=%s agent=%s domain=%s",
                tenant_id,
                agent_id,
                domain,
            )
            return True
        return False

    def enforce_write_domain(self, tenant_id: str, agent_id: str, domain: str) -> bool:
        if self.can_write_domain(tenant_id, agent_id, domain):
            return True
        if self.shadow_mode:
            logger.info(
                "policy_shadow_deny action=write tenant=%s agent=%s domain=%s",
                tenant_id,
                agent_id,
                domain,
            )
            return True
        return False


def agent_permissions_enabled() -> bool:
    return os.environ.get(env_vars.ENABLE_AGENT_PERMISSIONS, "0").strip() == "1"


def policy_shadow_mode_enabled() -> bool:
    return os.environ.get(env_vars.POLICY_SHADOW_MODE, "0").strip() == "1"


def validate_policy_configuration() -> None:
    if policy_shadow_mode_enabled():
        logger.warning(
            "shadow_mode_active: policy denials will be logged but not enforced; "
            "disable %s for production use",
            env_vars.POLICY_SHADOW_MODE,
        )
    if agent_permissions_enabled() and policy_shadow_mode_enabled() and multi_tenant_enabled():
        raise RuntimeError(
            f"{env_vars.POLICY_SHADOW_MODE} cannot be enabled with "
            f"{env_vars.ENABLE_AGENT_PERMISSIONS}=1 when multi-tenant mode is active"
        )
