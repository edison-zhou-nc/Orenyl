"""Rule version registry with active-version conflict checks."""

from __future__ import annotations

from .db import Database


class RuleRegistry:
    def __init__(self, db: Database):
        self.db = db

    def register(self, rule_family: str, version: str, active: bool = False) -> None:
        with self.db.transaction():
            if active and self.db.get_active_rule_versions(rule_family):
                raise ValueError("active_version_conflict")
            self.db.register_rule_version(rule_family, version, active=active)

    def deactivate(self, rule_family: str, version: str) -> None:
        self.db.set_rule_version_active(rule_family, version, active=False)

    def get_active_version(self, rule_family: str) -> str | None:
        active = self.db.get_active_rule_versions(rule_family)
        return active[0] if active else None
