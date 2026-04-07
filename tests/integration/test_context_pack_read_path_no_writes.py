import pytest

import orenyl.context_pack as context_pack_module
from orenyl.context_pack import ContextPackBuilder
from orenyl.db import Database
from orenyl.lineage import LineageEngine
from orenyl.models import Event


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


def test_context_pack_builder_rejects_legacy_env_vars(monkeypatch):
    db = Database(":memory:")

    class _Provider:
        provider_id = "provider:test"

        def embed_text(self, text: str):
            return [0.0]

    class _Backend:
        def query(self, namespace: str, query: list[float], top_k: int):
            return []

    with monkeypatch.context() as m:
        m.setenv("LORE_TRANSPORT", "stdio")
        m.setattr(context_pack_module, "_get_embedding_provider", lambda: _Provider())
        m.setattr(context_pack_module, "_get_vector_backend", lambda db: _Backend())

        with pytest.raises(RuntimeError, match="LORE_TRANSPORT"):
            ContextPackBuilder(db).build(domain="health", query="med")
