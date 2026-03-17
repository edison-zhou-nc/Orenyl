from lore.context_pack import ContextPackBuilder
from lore.db import Database
from lore.lineage import LineageEngine
from lore.models import Event


def test_context_pack_filters_by_agent_id_scope():
    db = Database(":memory:")
    engine = LineageEngine(db)

    e_agent_a = Event(
        id="event:test:scope:a",
        type="med_started",
        payload={"name": "metformin"},
        domains=["health"],
        metadata={"agent_id": "agent-a", "session_id": "s1"},
    )
    e_agent_b = Event(
        id="event:test:scope:b",
        type="role_assigned",
        payload={"user": "u", "role": "admin"},
        domains=["career"],
        metadata={"agent_id": "agent-b", "session_id": "s2"},
    )
    db.insert_event(e_agent_a)
    db.insert_event(e_agent_b)
    engine.derive_facts_for_event(db.get_event(e_agent_a.id))
    engine.derive_facts_for_event(db.get_event(e_agent_b.id))

    pack = ContextPackBuilder(db).build(domain="general", query="", agent_id="agent-a")
    keys = {f["key"] for f in pack.to_dict().get("facts", [])}

    assert "active_medications" in keys
    assert "current_role" not in keys


def test_context_pack_filters_by_session_id_scope():
    db = Database(":memory:")
    engine = LineageEngine(db)

    e1 = Event(
        id="event:test:scope:s1",
        type="med_started",
        payload={"name": "metformin"},
        domains=["health"],
        metadata={"agent_id": "agent-a", "session_id": "session-1"},
    )
    e2 = Event(
        id="event:test:scope:s2",
        type="med_started",
        payload={"name": "aspirin"},
        domains=["health"],
        metadata={"agent_id": "agent-a", "session_id": "session-2"},
    )
    db.insert_event(e1)
    db.insert_event(e2)
    engine.derive_facts_for_event(db.get_event(e1.id))
    engine.derive_facts_for_event(db.get_event(e2.id))

    pack = ContextPackBuilder(db).build(domain="health", query="", session_id="session-1")
    keys = {f["key"] for f in pack.to_dict().get("facts", [])}

    assert "active_medications" not in keys


def test_context_pack_returns_expected_fact_for_matching_session_scope():
    db = Database(":memory:")
    engine = LineageEngine(db)

    e1 = Event(
        id="event:test:scope:positive",
        type="role_assigned",
        payload={"user": "alice", "role": "admin"},
        domains=["career"],
        metadata={"agent_id": "agent-a", "session_id": "session-1"},
    )
    db.insert_event(e1)
    engine.derive_facts_for_event(db.get_event(e1.id))

    pack = ContextPackBuilder(db).build(domain="career", query="", session_id="session-1")
    keys = {f["key"] for f in pack.to_dict().get("facts", [])}
    assert "current_role" in keys
