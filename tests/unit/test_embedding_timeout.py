"""Tests for embedding timeout fallback."""

from __future__ import annotations

import threading
import time

import pytest

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


class ConcurrencyTrackingProvider:
    provider_id = "slow-concurrency-test"
    dim = 128

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.active_calls = 0
        self.max_active_calls = 0

    def embed_text(self, text: str) -> list[float]:
        with self._lock:
            self.active_calls += 1
            self.max_active_calls = max(self.max_active_calls, self.active_calls)
        try:
            time.sleep(0.2)
            return [0.0] * self.dim
        finally:
            with self._lock:
                self.active_calls -= 1


class BlockingEmbeddingProvider:
    provider_id = "blocking-test"
    dim = 128

    def __init__(self) -> None:
        self.started = threading.Event()
        self.release = threading.Event()
        self._lock = threading.Lock()
        self.started_calls = 0
        self.completed_calls = 0

    def embed_text(self, text: str) -> list[float]:
        with self._lock:
            self.started_calls += 1
        self.started.set()
        self.release.wait(timeout=1.0)
        with self._lock:
            self.completed_calls += 1
        return [0.0] * self.dim


@pytest.fixture(autouse=True)
def _reset_embedding_state():
    """Reset module-level executor and future between tests for clean isolation."""
    yield
    context_pack_module._reset_runtime_state_for_tests()


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


def test_embedding_timeout_reuses_single_worker_when_provider_is_stuck():
    """Repeated timeouts should not start overlapping embed calls."""
    provider = ConcurrencyTrackingProvider()

    for _ in range(3):
        with pytest.raises(TimeoutError):
            context_pack_module._embed_with_timeout(provider, "metformin", timeout=0.01)

    assert provider.max_active_calls == 1


def test_embedding_timeout_fails_fast_without_queueing_more_work():
    """Retries while the worker is still running should not enqueue additional work."""
    provider = BlockingEmbeddingProvider()

    with pytest.raises(TimeoutError, match="embedding_timeout_after_0.01_seconds"):
        context_pack_module._embed_with_timeout(provider, "metformin", timeout=0.01)

    assert provider.started.wait(timeout=0.1)

    started = time.perf_counter()
    with pytest.raises(TimeoutError, match="embedding_worker_busy"):
        context_pack_module._embed_with_timeout(provider, "metformin", timeout=0.01)
    elapsed = time.perf_counter() - started

    provider.release.set()
    time.sleep(0.05)

    assert elapsed < 0.05
    assert provider.started_calls == 1
    assert provider.completed_calls == 1
