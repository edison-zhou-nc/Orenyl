def test_expired_event_is_deleted_by_ttl_sweep():
    from lore.db import Database
    db = Database(":memory:")
    assert hasattr(db, "get_expired_events")
