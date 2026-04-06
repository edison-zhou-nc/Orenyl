from orenyl.db import Database
from orenyl.models import Fact
from orenyl.rule_migration import migrate_rule_family
from orenyl.rule_registry import RuleVersionRegistry


def test_migrate_rule_family_updates_fact_versions():
    db = Database(":memory:")
    registry = RuleVersionRegistry(db)
    registry.register("MedicationActiveRule", "v1", active=True)
    registry.deactivate("MedicationActiveRule", "v1")
    registry.register("MedicationActiveRule", "v2", active=True)

    db.insert_fact(
        Fact(
            id="fact:medication:1",
            key="active_medications",
            value=["metformin"],
            version=1,
            rule_id="MedicationActiveRule",
            rule_version="v1",
        )
    )

    out = migrate_rule_family(db, "MedicationActiveRule", from_version="v1", to_version="v2")
    assert out["migrated"] == 1

    fact = db.get_fact("fact:medication:1")
    assert fact is not None
    assert fact["rule_version"] == "v2"
