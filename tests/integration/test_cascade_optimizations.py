from lore.db import Database
from lore.lineage import LineageEngine


def test_skip_if_unchanged_increments_skip_counter():
    db = Database(":memory:")
    engine = LineageEngine(db)
    proof = engine.delete_and_recompute("event:missing", "event", reason="noop")
    proof_dict = proof.to_dict()
    assert proof_dict["checks"]["skip_count"] == 1
    assert proof_dict["checks"]["deletion_verified"] is True
    assert proof_dict["checks"]["stale_marked"] == 0
    assert proof_dict["checks"]["resurfaced_references"] == []
    assert proof_dict["checks"]["target_in_active_events"] is False
