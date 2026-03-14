from __future__ import annotations

from lore import audit
from lore.audit_anomaly import scan_access_anomalies


def test_anomaly_detection_flags_denied_spike():
    audit.clear_events()
    for idx in range(2):
        audit.log_security_event(
            "list_events",
            "allow",
            principal_id="agent-a",
            request_id=f"req-allow-{idx}",
        )
    for idx in range(6):
        audit.log_security_event(
            "export_domain",
            "deny",
            principal_id="agent-a",
            request_id=f"req-deny-{idx}",
        )

    alerts = scan_access_anomalies(audit.get_events(limit=100))
    assert alerts
    assert any(alert["type"] == "deny_spike" for alert in alerts)
