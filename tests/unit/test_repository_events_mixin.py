from lore.db import Database
from lore.models import Event


def test_event_repository_round_trips_payload_domains_and_updates():
    db = Database(":memory:")
    event = Event(
        id="event:test:repo-e1",
        type="note",
        payload={"text": "hello"},
        domains=["health", "general"],
        metadata={"subject_id": "user:1"},
    )

    db.insert_event(event)
    stored = db.get_event(event.id)

    assert stored is not None
    assert stored["payload"] == {"text": "hello"}
    assert stored["domains"] == ["general", "health"]
    assert db.get_active_domains_by_subject("user:1") == {"general", "health"}

    assert db.update_event_payload(event.id, {"text": "updated"}) is True
    assert db.get_event(event.id)["payload"] == {"text": "updated"}
