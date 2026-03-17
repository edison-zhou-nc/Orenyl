"""Dedicated summary derivation rule for domain narratives."""

from __future__ import annotations

from .base_rule import DerivationRule


class DomainSummaryRule(DerivationRule):
    rule_id = "DomainSummaryRule@v1"
    output_key = "domain_summary"

    def relevant_event_types(self) -> list[str]:
        return [
            "note",
            "med_started",
            "med_discontinued",
            "role_assigned",
            "role_revoked",
            "diet_preference",
        ]

    def derive(self, events: list[dict]) -> dict:
        if not events:
            return {"summary": ""}

        latest_by_type: dict[str, dict] = {}
        notes: list[dict] = []
        for event in sorted(events, key=lambda e: e.get("ts", "")):
            etype = event.get("type", "")
            if etype == "note":
                notes.append(event)
                continue
            latest_by_type[etype] = event

        parts: list[str] = []
        if "diet_preference" in latest_by_type:
            value = latest_by_type["diet_preference"].get("payload", {}).get("value")
            if value:
                parts.append(f"diet_preference={value}")

        if "med_started" in latest_by_type:
            med = latest_by_type["med_started"].get("payload", {}).get("name")
            if med:
                parts.append(f"med_started={med}")
        if "med_discontinued" in latest_by_type:
            med = latest_by_type["med_discontinued"].get("payload", {}).get("name")
            if med:
                parts.append(f"med_discontinued={med}")

        if "role_assigned" in latest_by_type:
            payload = latest_by_type["role_assigned"].get("payload", {})
            user = payload.get("user", "")
            role = payload.get("role", "")
            if user or role:
                parts.append(f"role_assigned={user}:{role}")
        if "role_revoked" in latest_by_type:
            user = latest_by_type["role_revoked"].get("payload", {}).get("user", "")
            if user:
                parts.append(f"role_revoked={user}")

        for note in notes[-3:]:
            if (note.get("sensitivity") or "").lower() in {"high", "restricted"}:
                continue
            text = str(note.get("payload", {}).get("text", "")).strip()
            if text:
                parts.append(f"note={text}")

        summary = "; ".join(parts)
        return {"summary": summary[:300]}
