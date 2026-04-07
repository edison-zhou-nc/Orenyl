from orenyl.db import Database
from orenyl.policy import PolicyEngine


def test_expired_delegation_is_not_honored():
    db = Database(":memory:")
    db.conn.execute(
        """INSERT INTO delegation_grants (
               tenant_id, grantor_agent_id, grantee_agent_id, domain, action, expires_at
           ) VALUES (?, ?, ?, ?, ?, ?)""",
        ("tenant-a", "agent-owner", "agent-b", "health", "read", "2026-03-11T23:59:59Z"),
    )
    db.conn.commit()
    policy = PolicyEngine(db, shadow_mode=False)

    assert (
        policy.can_delegate_read(
            "tenant-a",
            "agent-b",
            "health",
            now="2026-03-12T00:00:00Z",
        )
        is False
    )
