from __future__ import annotations

from lore import audit


def test_audit_log_hash_chain_detects_tamper():
    audit.clear_events()
    audit.log_security_event("list_events", "allow", principal_id="agent-a", request_id="req-1")
    audit.log_security_event("store_event", "deny", principal_id="agent-a", request_id="req-2")

    assert audit.verify_hash_chain() is True

    conn = audit._conn()
    conn.execute(
        "UPDATE security_audit_events SET details_json = ? WHERE request_id = ?",
        ('{"tampered":true}', "req-1"),
    )
    conn.commit()

    assert audit.verify_hash_chain() is False
