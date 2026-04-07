from orenyl import context_pack as context_pack_module
from orenyl.context_pack import ContextPackBuilder
from orenyl.db import Database
from orenyl.lineage import LineageEngine
from orenyl.models import Event


class _TinyProvider:
    provider_id = "tiny-provider"
    dim = 2

    def embed_text(self, text: str) -> list[float]:
        return [1.0, 0.0]


def test_context_pack_warns_and_skips_stored_embedding_model_mismatch(monkeypatch, caplog):
    db = Database(":memory:")
    engine = LineageEngine(db)
    ev = Event(
        id="event:test:model-mismatch",
        type="med_started",
        payload={"name": "metformin"},
        domains=["health"],
    )
    db.insert_event(ev)
    engine.derive_facts_for_event(db.get_event(ev.id))
    fact = db.get_current_facts("active_medications")[0]
    db.upsert_fact_embedding(fact["id"], [0.1, 0.2], model_id="other-provider")

    caplog.set_level("WARNING")
    monkeypatch.setattr(context_pack_module, "_get_embedding_provider", lambda: _TinyProvider())

    pack = ContextPackBuilder(db).build(domain="health", query="med")
    assert pack.items
    assert any("model_mismatch" in record.message for record in caplog.records)
