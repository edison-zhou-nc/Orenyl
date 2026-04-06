from orenyl.db import Database
from orenyl.models import Event, Fact


def test_upsert_and_fetch_event_embedding():
    db = Database(":memory:")
    db.insert_event(Event(id="event:test:e1", type="note", payload={"text": "hello"}))
    db.upsert_event_embedding("event:test:e1", [0.1, 0.2], "hash-local")
    embedding = db.get_event_embedding("event:test:e1")
    assert embedding is not None
    assert embedding["event_id"] == "event:test:e1"
    assert embedding["model_id"] == "hash-local"
    assert embedding["vector"] == [0.1, 0.2]


def test_upsert_and_fetch_fact_embeddings():
    db = Database(":memory:")
    db.insert_fact(Fact(id="fact:test:f1", key="a", value={"v": 1}, rule_id="Rule@v1"))
    db.insert_fact(Fact(id="fact:test:f2", key="b", value={"v": 2}, rule_id="Rule@v1"))
    db.upsert_fact_embedding("fact:test:f1", [0.2, 0.3], "hash-local")
    db.upsert_fact_embedding("fact:test:f2", [0.4, 0.5], "hash-local")
    rows = db.get_fact_embeddings(["fact:test:f1", "fact:test:f2"])
    assert rows["fact:test:f1"]["vector"] == [0.2, 0.3]
    assert rows["fact:test:f2"]["vector"] == [0.4, 0.5]
