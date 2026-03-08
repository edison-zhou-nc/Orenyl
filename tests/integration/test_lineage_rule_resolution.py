from lore.db import Database
from lore.lineage import LineageEngine
from lore.models import Event


def test_v1_event_without_domains_still_derives_from_event_type():
    db = Database(":memory:")
    engine = LineageEngine(db)

    ev = Event(
        id="event:med_started:v1",
        type="med_started",
        payload={"name": "metformin"},
    )
    db.insert_event(ev)
    engine.derive_facts_for_event(db.get_event(ev.id))

    facts = db.get_current_facts("active_medications")
    assert len(facts) == 1
    assert "metformin" in facts[0]["value"]


def test_delete_recompute_uses_same_rule_resolution_for_domain_events():
    db = Database(":memory:")
    engine = LineageEngine(db)

    ev1 = Event(id="event:note:1", type="note", payload={"text": "first"}, domains=["career"])
    ev2 = Event(id="event:note:2", type="note", payload={"text": "second"}, domains=["career"])
    db.insert_event(ev1)
    db.insert_event(ev2)

    engine.derive_facts_for_event(db.get_event(ev1.id))
    engine.derive_facts_for_event(db.get_event(ev2.id))

    before = db.get_current_facts("current_role")
    assert len(before) == 1

    engine.delete_and_recompute(ev1.id, "event", reason="cleanup")

    after = db.get_current_facts("current_role")
    assert len(after) == 1


def test_delete_recompute_reruns_all_rules_and_records_single_proof_per_rule():
    db = Database(":memory:")
    engine = LineageEngine(db)

    ev1 = Event(id="event:mix:1", type="med_started", payload={"name": "metformin"}, domains=["health"])
    ev2 = Event(id="event:mix:2", type="note", payload={"text": "taking med"}, domains=["health"])
    db.insert_event(ev1)
    db.insert_event(ev2)
    engine.derive_facts_for_event(db.get_event(ev1.id))
    engine.derive_facts_for_event(db.get_event(ev2.id))

    proof = engine.delete_and_recompute(ev1.id, "event", reason="cleanup")
    keys = [item["key"] for item in proof.rederived_facts]

    assert "active_medications" in keys
    assert "domain_summary" in keys
    assert len(keys) == len(set(keys))

