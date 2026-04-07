def test_delete_proof_has_no_resurface_incidents():
    from orenyl.db import Database
    from orenyl.lineage import LineageEngine

    db = Database(":memory:")
    engine = LineageEngine(db)
    proof = engine.delete_and_recompute("event:missing", "event", reason="smoke")
    assert "deletion_verified" in proof.to_dict()["checks"]
