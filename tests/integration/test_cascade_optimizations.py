from lore.db import Database
from lore.lineage import LineageEngine


def test_skip_if_unchanged_increments_skip_counter():
    db = Database(":memory:")
    engine = LineageEngine(db)
    proof = engine.delete_and_recompute("event:missing", "event", reason="noop")
    assert "skip_count" in proof.to_dict()["checks"]

