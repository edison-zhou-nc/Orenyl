import logging

from orenyl.db import Database
from orenyl.policy import PolicyEngine


def test_policy_denies_agent_without_domain_read_grant():
    db = Database(":memory:")
    policy = PolicyEngine(db, shadow_mode=False)

    allowed = policy.can_read_domain("tenant-a", "agent-a", "health")

    assert allowed is False


def test_policy_denies_agent_without_domain_write_grant():
    db = Database(":memory:")
    policy = PolicyEngine(db, shadow_mode=False)

    allowed = policy.can_write_domain("tenant-a", "agent-a", "health")

    assert allowed is False


def test_policy_shadow_mode_logs_deny_but_returns_ok(caplog):
    db = Database(":memory:")
    policy = PolicyEngine(db, shadow_mode=True)
    caplog.set_level(logging.INFO)

    allowed = policy.enforce_read_domain("tenant-a", "agent-a", "health")

    assert allowed is True
    assert "policy_shadow_deny" in caplog.text
