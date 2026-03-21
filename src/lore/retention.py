"""Retention lifecycle policy helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .db import Database


def _parse_iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)


def _age_days(ts: str, now_ts: str) -> int:
    """Return whole-day age using timedelta.days (fractional days are truncated)."""
    delta = _parse_iso(now_ts) - _parse_iso(ts)
    return max(0, delta.days)


def _next_tier(age_days: int, policy: dict[str, int]) -> str:
    if age_days >= int(policy.get("delete_days", 36500)):
        return "delete"
    if age_days >= int(policy.get("archive_days", 36500)):
        return "archive"
    if age_days >= int(policy.get("warm_days", 36500)):
        return "warm"
    return "hot"


def apply_retention_policies(
    events: list[dict[str, Any]],
    now_ts: str,
    policies: dict[str, dict[str, int]],
) -> dict[str, dict[str, str]]:
    tiers: dict[str, str] = {}
    for event in events:
        domains = event.get("domains") or ["general"]
        selected: dict[str, int] | None = None
        for domain in domains:
            candidate = policies.get(domain)
            if not candidate:
                continue
            if selected is None:
                selected = candidate
                continue
            if int(candidate.get("delete_days", 36500)) < int(selected.get("delete_days", 36500)):
                selected = candidate
        policy = selected or policies.get("default", {})
        tier = _next_tier(_age_days(str(event["ts"]), now_ts), policy)
        tiers[str(event["id"])] = tier
    return {"tiers": tiers}


def apply_retention_to_db(
    db: Database,
    now_ts: str,
    policies: dict[str, dict[str, int]],
    tenant_id: str = "",
) -> dict[str, int]:
    events = db.get_active_events(tenant_id=tenant_id)
    evaluated = apply_retention_policies(events, now_ts=now_ts, policies=policies)
    archived = 0
    deleted = 0
    updated = 0
    for event in events:
        event_id = event["id"]
        target_tier = evaluated["tiers"][event_id]
        if target_tier == "delete":
            if db.soft_delete_event(event_id, now_ts, tenant_id=tenant_id):
                deleted += 1
                updated += 1
            continue
        archived_at = now_ts if target_tier == "archive" else None
        if db.update_event_retention(
            event_id,
            target_tier,
            archived_at,
            tenant_id=tenant_id,
        ):
            if target_tier == "archive":
                archived += 1
            updated += 1
    return {"updated": updated, "archived": archived, "deleted": deleted}
