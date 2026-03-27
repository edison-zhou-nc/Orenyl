from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace

import scripts.run_benchmarks as run_benchmarks


class FakeDatabase:
    def __init__(self, _db_path: str = ":memory:") -> None:
        self.events: dict[str, dict] = {}
        self.fact_ids: list[str] = []
        self.edge_pairs: list[tuple[str, str]] = []

    @contextmanager
    def transaction(self):
        yield

    def insert_event(self, event) -> None:
        self.events[event.id] = {
            "id": event.id,
            "type": event.type,
            "payload": event.payload,
            "domains": list(event.domains),
            "tenant_id": getattr(event, "tenant_id", "default"),
        }

    def get_event(self, event_id: str) -> dict:
        return self.events[event_id]

    def insert_fact(self, fact) -> str:
        self.fact_ids.append(fact.id)
        return fact.id

    def insert_edge(self, edge) -> None:
        self.edge_pairs.append((edge.parent_id, edge.child_id))


class FakeProof:
    def to_dict(self) -> dict:
        return {"checks": {"deletion_verified": True}}


class FakeEngine:
    last_instance: FakeEngine | None = None

    def __init__(self, db) -> None:
        self.db = db
        self.derived_event_ids: list[str] = []
        self.deleted_event_ids: list[str] = []
        FakeEngine.last_instance = self

    def derive_facts_for_event(self, event: dict) -> list[str]:
        self.derived_event_ids.append(event["id"])
        return []

    def delete_and_recompute(self, target_id: str, *_args, **_kwargs):
        self.deleted_event_ids.append(target_id)
        return FakeProof()


class FakeBuilder:
    def __init__(self, db) -> None:
        self.db = db

    def build(self, **_kwargs):
        return SimpleNamespace(items=[{"id": fact_id} for fact_id in self.db.fact_ids])


def test_run_scale_populates_corpus_without_streaming_derivation(monkeypatch):
    monkeypatch.setattr(run_benchmarks, "Database", FakeDatabase)
    monkeypatch.setattr(run_benchmarks, "LineageEngine", FakeEngine)
    monkeypatch.setattr(run_benchmarks, "ContextPackBuilder", FakeBuilder)

    result = run_benchmarks.run_scale(5)

    assert FakeEngine.last_instance is not None
    assert FakeEngine.last_instance.derived_event_ids == ["event:bench:probe"]
    assert FakeEngine.last_instance.deleted_event_ids == ["event:bench:probe"]
    assert result["deletion_verified"] is True
    assert result["context_pack_items"] == 5
    assert isinstance(result["insert_and_derive_single_event_ms"], float)
    assert isinstance(result["retrieve_context_pack_ms"], float)
    assert isinstance(result["delete_and_recompute_ms"], float)
    assert len(FakeEngine.last_instance.db.fact_ids) == 5
    assert len(FakeEngine.last_instance.db.edge_pairs) == 5


def test_baseline_artifact_metrics_uses_run_scale_output(monkeypatch):
    def fake_run_scale(n_events: int) -> dict:
        assert n_events == 1000
        return {
            "events": 1000,
            "insert_and_derive_single_event_ms": 123.4,
            "retrieve_context_pack_ms": 56.7,
            "delete_and_recompute_ms": 89.0,
            "deletion_verified": True,
            "context_pack_items": 42,
        }

    monkeypatch.setattr(run_benchmarks, "run_scale", fake_run_scale)

    result = run_benchmarks.baseline_artifact_metrics(1000)

    assert result == {
        "event_count": 1000,
        "store_seconds": 0.1234,
        "retrieve_seconds": 0.0567,
        "delete_seconds": 0.089,
        "health_fact_count": 42,
        "deletion_verified": True,
    }
