"""Tests for embedding timeout fallback."""

from __future__ import annotations

import time

from lore import context_pack as context_pack_module
from lore.context_pack import ContextPackBuilder
from lore.db import Database
from lore.lineage import LineageEngine
from lore.models import Event


class SlowEmbeddingProvider:
    provider_id = "slow-test"
    dim = 128

    def embed_text(self, text: str) -> list[float]:
        time.sleep(0.2)
        return [0.0] * self.dim


def test_embedding_timeout_falls_back_to_keyword_ranking(monkeypatch):
    """Slow embedding calls should time out and fall back quickly to keyword ranking."""
    db = Database(":memory:")
    engine = LineageEngine(db)
    builder = ContextPackBuilder(db)

    event = Event(
        id="event:timeout:1",
        type="med_started",
        payload={"name": "metformin"},
        domains=["health"],
        sensitivity="medium",
    )
    db.insert_event(event)
    engine.derive_facts_for_event(db.get_event(event.id))

    monkeypatch.setattr(context_pack_module, "_embedding_provider", None)
    monkeypatch.setattr(context_pack_module, "_get_embedding_provider", lambda: SlowEmbeddingProvider())
    monkeypatch.setattr(context_pack_module, "_EMBEDDING_TIMEOUT_SECONDS", 0.01, raising=False)

    started = time.perf_counter()
    pack = builder.build(
        domain="health",
        query="metformin",
        limit=10,
    )
    elapsed = time.perf_counter() - started

    assert elapsed < 0.5
    assert pack.domain == "health"
    assert pack.items
