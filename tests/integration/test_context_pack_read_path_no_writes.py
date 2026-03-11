from lore.context_pack import ContextPackBuilder
from lore.db import Database
from lore.lineage import LineageEngine
from lore.models import Event


def test_context_pack_build_does_not_backfill_embeddings(monkeypatch):
    db = Database(":memory:")
    engine = LineageEngine(db)

    ev = Event(
        id="event:test:readonly-pack",
        type="med_started",
        payload={"name": "metformin"},
        domains=["health"],
    )
    db.insert_event(ev)
    engine.derive_facts_for_event(db.get_event(ev.id))

    def _forbidden_write(*args, **kwargs):
        raise AssertionError("read path should not upsert fact embeddings")

    monkeypatch.setattr(db, "upsert_fact_embedding", _forbidden_write)
    pack = ContextPackBuilder(db).build(domain="health", query="med")
    assert pack.items
