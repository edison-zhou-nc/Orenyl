"""Article 30 (GDPR) processing record generation."""

from __future__ import annotations

from typing import Any

from .db import Database


def generate_article30_report(db: Database, tenant_id: str = "default") -> dict[str, Any]:
    events = db.get_active_events(tenant_id=tenant_id)
    domains = sorted({domain for event in events for domain in event.get("domains", [])})
    retention_tiers = sorted({str(event.get("retention_tier", "hot") or "hot") for event in events})

    purpose_rows = db.list_consent_purposes(tenant_id=tenant_id)
    purposes = [str(row["purpose"]) for row in purpose_rows if row["purpose"]]
    legal_bases = sorted(
        {str(row["legal_basis"]) for row in purpose_rows if str(row["legal_basis"] or "").strip()}
    )

    sync_count = db.sync_journal_count(tenant_id=tenant_id)
    recipients = ["mcp_client_runtime"]
    if int(sync_count or 0) > 0:
        recipients.append("federation_peer")

    return {
        "controller": "Lore Tenant Controller",
        "tenant_id": tenant_id,
        "purposes": purposes,
        "legal_bases": legal_bases,
        "data_categories": domains,
        "retention_policies": retention_tiers,
        "recipients": recipients,
        "cross_border_transfers": [],
        "security_measures": [
            "audit_logging",
            "lineage_tracking",
            "sensitivity_controls",
        ],
    }
