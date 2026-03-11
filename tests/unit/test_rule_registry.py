import pytest

from lore.db import Database
from lore.rule_registry import RuleRegistry


def test_rule_registry_prevents_two_active_versions_for_same_family():
    db = Database(":memory:")
    registry = RuleRegistry(db)
    registry.register("MedicationActiveRule", "v1", active=True)

    with pytest.raises(ValueError, match="active_version_conflict"):
        registry.register("MedicationActiveRule", "v2", active=True)


def test_rule_registry_allows_promote_after_deactivate():
    db = Database(":memory:")
    registry = RuleRegistry(db)
    registry.register("MedicationActiveRule", "v1", active=True)
    registry.deactivate("MedicationActiveRule", "v1")
    registry.register("MedicationActiveRule", "v2", active=True)

    active = registry.get_active_version("MedicationActiveRule")
    assert active == "v2"


def test_rule_registry_register_wraps_check_and_write_in_transaction(monkeypatch):
    db = Database(":memory:")
    registry = RuleRegistry(db)
    observed = {"entered": 0}
    original = db.transaction

    def _wrapped_transaction():
        observed["entered"] += 1
        return original()

    monkeypatch.setattr(db, "transaction", _wrapped_transaction)
    registry.register("MedicationActiveRule", "v1", active=True)
    assert observed["entered"] == 1
