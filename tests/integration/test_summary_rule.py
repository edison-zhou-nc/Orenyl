from lore.db import Database
from lore.lineage import LineageEngine
from lore.models import Event


def test_domain_summary_fact_is_created():
    db = Database(":memory:")
    engine = LineageEngine(db)
    ev = Event(
        id="event:test:sum1", type="note", payload={"text": "started metformin and feel better"}
    )
    ev.domains = ["health"]
    db.insert_event(ev)
    engine.derive_facts_for_event(db.get_event(ev.id))
    facts = db.get_current_facts()
    assert any(f["key"] == "domain_summary" for f in facts)


def test_domain_summary_tracks_latest_preference_without_resurfacing_superseded_value():
    db = Database(":memory:")
    engine = LineageEngine(db)

    first = Event(
        id="event:test:pref1",
        type="diet_preference",
        payload={"value": "vegan"},
        ts="2026-01-02T09:00:00Z",
        domains=["preferences"],
    )
    second = Event(
        id="event:test:pref2",
        type="diet_preference",
        payload={"value": "omnivore"},
        ts="2026-01-02T10:00:00Z",
        domains=["preferences"],
    )
    db.insert_event(first)
    engine.derive_facts_for_event(db.get_event(first.id))
    db.insert_event(second)
    engine.derive_facts_for_event(db.get_event(second.id))

    summary = db.get_current_facts("domain_summary")[0]["value"]["summary"]
    assert "omnivore" in summary
    assert "vegan" not in summary


def test_domain_summary_omits_high_sensitivity_note_text():
    db = Database(":memory:")
    engine = LineageEngine(db)

    ev = Event(
        id="event:test:high-note",
        type="note",
        payload={"text": "highly sensitive diagnosis details"},
        domains=["health"],
        sensitivity="high",
    )
    db.insert_event(ev)
    engine.derive_facts_for_event(db.get_event(ev.id))

    summary = db.get_current_facts("domain_summary")[0]["value"]["summary"]
    assert "highly sensitive diagnosis details" not in summary
