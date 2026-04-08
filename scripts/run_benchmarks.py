"""Run orenyl benchmarks at multiple scales and print results."""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from orenyl.context_pack import ContextPackBuilder
from orenyl.db import Database
from orenyl.lineage import LineageEngine
from orenyl.models import Edge, Event, Fact

DOMAINS = ["health", "career", "finance", "relationships", "preferences", "decisions"]


def _make_event(event_id: str, index: int) -> Event:
    return Event(
        id=event_id,
        type="note",
        payload={"text": f"Benchmark event {index} about health topic {index % len(DOMAINS)}"},
        domains=[DOMAINS[index % len(DOMAINS)]],
        sensitivity="medium",
    )


def _populate_corpus(db: Database, n_events: int) -> None:
    with db.transaction():
        for i in range(n_events):
            event = _make_event(f"event:bench:{i}", i)
            db.insert_event(event)
            fact = Fact(
                id=f"fact:bench:{i}",
                key=f"benchmark_note_{i}",
                value={"text": event.payload["text"]},
                version=1,
                rule_id="BenchmarkSeedRule@v1",
                tenant_id=event.tenant_id,
            )
            db.insert_fact(fact)
            db.insert_edge(
                Edge(
                    tenant_id=event.tenant_id,
                    parent_id=event.id,
                    parent_type="event",
                    child_id=fact.id,
                    child_type="fact",
                )
            )


def run_scale(n_events: int) -> dict:
    db = Database(":memory:")
    engine = LineageEngine(db)
    builder = ContextPackBuilder(db)
    _populate_corpus(db, n_events)

    probe_id = "event:bench:probe"
    probe_event = _make_event(probe_id, n_events)

    # Measure a single event ingest at corpus size N.
    t0 = time.perf_counter()
    db.insert_event(probe_event)
    engine.derive_facts_for_event(db.get_event(probe_id))
    ingest_time = time.perf_counter() - t0

    # Retrieve context pack
    t0 = time.perf_counter()
    pack = builder.build(domain="health", query="benchmark", limit=50)
    retrieve_time = time.perf_counter() - t0

    # Delete and recompute the measured event.
    t0 = time.perf_counter()
    proof = engine.delete_and_recompute(probe_id, "event", reason="benchmark", mode="soft")
    delete_time = time.perf_counter() - t0

    return {
        "events": n_events,
        "insert_and_derive_single_event_ms": round(ingest_time * 1000, 1),
        "retrieve_context_pack_ms": round(retrieve_time * 1000, 1),
        "delete_and_recompute_ms": round(delete_time * 1000, 1),
        "deletion_verified": proof.to_dict().get("checks", {}).get("deletion_verified"),
        "context_pack_items": len(pack.items),
    }


def baseline_artifact_metrics(n_events: int) -> dict[str, float | int | bool]:
    result = run_scale(n_events)
    return {
        "event_count": int(result["events"]),
        "store_seconds": round(float(result["insert_and_derive_single_event_ms"]) / 1000.0, 4),
        "retrieve_seconds": round(float(result["retrieve_context_pack_ms"]) / 1000.0, 4),
        "delete_seconds": round(float(result["delete_and_recompute_ms"]) / 1000.0, 4),
        "health_fact_count": int(result["context_pack_items"]),
        "deletion_verified": bool(result["deletion_verified"]),
    }


def main() -> None:
    scales = [1_000, 10_000, 100_000]
    results = []
    for n in scales:
        print(f"Running {n:,} events...", flush=True)
        result = run_scale(n)
        results.append(result)
        print(f"  insert+derive: {result['insert_and_derive_single_event_ms']}ms")
        print(f"  retrieve:     {result['retrieve_context_pack_ms']}ms")
        print(f"  delete:       {result['delete_and_recompute_ms']}ms")

    print("\n## Results (copy to docs/benchmarks/v2-baseline.md)\n")
    print("| Operation | 1K events | 10K events | 100K events |")
    print("|-----------|-----------|------------|-------------|")
    print(
        f"| insert + derive (single event) | "
        f"{results[0]['insert_and_derive_single_event_ms']}ms | "
        f"{results[1]['insert_and_derive_single_event_ms']}ms | "
        f"{results[2]['insert_and_derive_single_event_ms']}ms |"
    )
    print(
        f"| retrieve_context_pack | {results[0]['retrieve_context_pack_ms']}ms | "
        f"{results[1]['retrieve_context_pack_ms']}ms | {results[2]['retrieve_context_pack_ms']}ms |"
    )
    print(
        f"| delete_and_recompute | {results[0]['delete_and_recompute_ms']}ms | "
        f"{results[1]['delete_and_recompute_ms']}ms | {results[2]['delete_and_recompute_ms']}ms |"
    )
    print(
        f"| deletion_verified | {results[0]['deletion_verified']} | "
        f"{results[1]['deletion_verified']} | {results[2]['deletion_verified']} |"
    )


if __name__ == "__main__":
    main()
