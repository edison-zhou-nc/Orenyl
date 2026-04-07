from orenyl.models import Event, Fact


def test_event_and_fact_have_v2_fields():
    event = Event(id="event:test:1", type="note", payload={"x": 1})
    assert hasattr(event, "content_hash")
    assert hasattr(event, "sensitivity")
    assert hasattr(event, "consent_source")
    assert hasattr(event, "expires_at")
    assert hasattr(event, "domains")
    assert event.domains == []
    assert event.content_hash is None
    assert event.sensitivity == "medium"
    assert event.consent_source == "implicit"
    assert event.expires_at is None

    fact = Fact(id="fact:test:v1", key="k", value={})
    assert hasattr(fact, "transform_config")
    assert hasattr(fact, "stale")
    assert hasattr(fact, "importance")
    assert fact.transform_config == {}
    assert fact.stale is False
    assert fact.importance == 0.5
