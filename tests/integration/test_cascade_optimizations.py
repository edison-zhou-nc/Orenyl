from lore.db import Database
from lore.lineage import LineageEngine


def test_skip_if_unchanged_increments_skip_counter():
    db = Database(":memory:")
    engine = LineageEngine(db)
    proof = engine.delete_and_recompute("event:missing", "event", reason="noop")
    assert proof.to_dict()["checks"]["skip_count"] == 1
    assert proof.to_dict()["checks"]["deletion_verified"] is True
