"""Agent/domain policy enforcement."""

from __future__ import annotations

import logging
import os

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

    def enforce_read_domain(self, tenant_id: str, agent_id: str, domain: str) -> bool:
        if self.can_read_domain(tenant_id, agent_id, domain):
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
    return os.environ.get("LORE_ENABLE_AGENT_PERMISSIONS", "0").strip() == "1"


def policy_shadow_mode_enabled() -> bool:
    return os.environ.get("LORE_POLICY_SHADOW_MODE", "0").strip() == "1"
