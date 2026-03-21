"""Rule migration helpers for explicit version upgrades."""

from __future__ import annotations

from .db import Database


def migrate_rule_family(
    db: Database,
    rule_family: str,
    from_version: str,
    to_version: str,
    tenant_id: str = "",
) -> dict[str, int]:
    facts = db.list_current_facts_by_rule_family(rule_family, from_version, tenant_id=tenant_id)
    migrated = 0
    for fact in facts:
        if db.update_fact_rule_version(fact["id"], to_version, tenant_id=tenant_id):
            migrated += 1
    return {"checked": len(facts), "migrated": migrated}
