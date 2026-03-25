"""Deterministic derivation rules for Lore governed memory.

Each rule takes active events and produces facts.
Rules are pure functions: same events → same facts. Always.
"""

from __future__ import annotations

from typing import Any

from .base_rule import DerivationRule
from .domain_registry import CORE_DOMAINS
from .summary_rule import DomainSummaryRule


class MedicationActiveRule(DerivationRule):
    """Domain 1: Medication tracking.

    active_medications = started meds minus discontinued meds.
    """

    rule_id = "MedicationActiveRule@v1"
    output_key = "active_medications"

    def relevant_event_types(self) -> list[str]:
        return ["med_started", "med_discontinued"]

    def derive(self, events: list[dict]) -> list[str]:
        started: dict[str, str] = {}  # med_name -> latest start timestamp
        discontinued: dict[str, str] = {}  # med_name -> latest discontinue timestamp

        for e in events:
            if e["type"] == "med_started":
                name = e["payload"].get("name", "")
                if name:
                    ts = e["ts"]
                    if name not in started or ts > started[name]:
                        started[name] = ts

            elif e["type"] == "med_discontinued":
                name = e["payload"].get("name", "")
                if name:
                    ts = e["ts"]
                    if name not in discontinued or ts > discontinued[name]:
                        discontinued[name] = ts

        active = []
        for name, start_ts in sorted(started.items()):
            disc_ts = discontinued.get(name)
            if disc_ts is None or disc_ts < start_ts:
                active.append(name)

        return sorted(active)


class CurrentRoleRule(DerivationRule):
    """Domain 2: Role/permission tracking.

    current_role = latest role_assigned event. role_revoked clears it.
    """

    rule_id = "CurrentRoleRule@v1"
    output_key = "current_role"

    def relevant_event_types(self) -> list[str]:
        return ["role_assigned", "role_revoked"]

    def derive(self, events: list[dict]) -> dict[str, Any]:
        latest_ts = ""
        latest_role: str | None = None
        latest_user: str = ""

        for e in events:
            ts = e["ts"]
            if ts >= latest_ts:
                latest_ts = ts
                if e["type"] == "role_assigned":
                    latest_role = e["payload"].get("role", "")
                    latest_user = e["payload"].get("user", "")
                elif e["type"] == "role_revoked":
                    latest_role = None
                    latest_user = e["payload"].get("user", "")

        return {
            "user": latest_user,
            "role": latest_role,
            "active": latest_role is not None,
        }


class DietPreferenceRule(DerivationRule):
    """Domain 3: Preference tracking (latest-event-wins).

    diet_preference = value from most recent diet_preference event.
    """

    rule_id = "DietPreferenceRule@v1"
    output_key = "diet_preference"

    def relevant_event_types(self) -> list[str]:
        return ["diet_preference"]

    def derive(self, events: list[dict]) -> dict[str, Any]:
        latest_ts = ""
        latest_value = None

        for e in events:
            if e["type"] == "diet_preference" and e["ts"] >= latest_ts:
                latest_ts = e["ts"]
                latest_value = e["payload"].get("value")

        return {
            "value": latest_value,
            "since": latest_ts if latest_value else None,
        }


_summary_rule = DomainSummaryRule()

ALL_RULES: list[DerivationRule] = [
    MedicationActiveRule(),
    CurrentRoleRule(),
    DietPreferenceRule(),
    _summary_rule,
]

RULES_BY_KEY: dict[str, DerivationRule] = {r.output_key: r for r in ALL_RULES}


class RuleRegistry:
    def __init__(self):
        self._by_domain: dict[str, list[DerivationRule]] = {}

    def register_rule(self, domain: str, rule: DerivationRule):
        key = (domain or "general").strip().lower()
        self._by_domain.setdefault(key, []).append(rule)

    def get_rules_for_domains(self, domains: list[str]) -> list[DerivationRule]:
        keys = [(d or "").strip().lower() for d in (domains or []) if (d or "").strip()]
        if not keys:
            keys = ["general"]
        seen: set[str] = set()
        result: list[DerivationRule] = []
        for key in keys:
            for rule in self._by_domain.get(key, []):
                if rule.output_key not in seen:
                    seen.add(rule.output_key)
                    result.append(rule)
        if not result:
            for rule in self._by_domain.get("general", []):
                if rule.output_key not in seen:
                    seen.add(rule.output_key)
                    result.append(rule)
        return result


RULE_REGISTRY = RuleRegistry()
for _rule in ALL_RULES:
    RULE_REGISTRY.register_rule("general", _rule)

RULE_REGISTRY.register_rule("health", RULES_BY_KEY["active_medications"])
RULE_REGISTRY.register_rule("career", RULES_BY_KEY["current_role"])
RULE_REGISTRY.register_rule("preferences", RULES_BY_KEY["diet_preference"])

for _domain in CORE_DOMAINS:
    RULE_REGISTRY.register_rule(_domain, _summary_rule)


def get_rules_for_event_type(event_type: str) -> list[DerivationRule]:
    """Find which rules need to re-derive when an event of this type changes."""
    return [r for r in ALL_RULES if event_type in r.relevant_event_types()]
