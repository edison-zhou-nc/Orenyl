import json
import os
import time
from pathlib import Path

from lore.context_pack import ContextPackBuilder
from lore.db import Database
from lore.lineage import LineageEngine
from lore.models import Event


def test_scale_benchmark_generates_baseline_artifact(workspace_tmp_path):
    db = Database(":memory:")
    engine = LineageEngine(db)
    builder = ContextPackBuilder(db)

    domains = ["health", "career", "finance", "relationships", "preferences", "decisions"]

    start_store = time.perf_counter()
    for i in range(1000):
        domain = domains[i % len(domains)]
        event = Event(
            id=f"event:bench:{i}",
            type="note",
            payload={"text": f"benchmark item {i}"},
            domains=[domain],
        )
        db.insert_event(event)
        engine.derive_facts_for_event(db.get_event(event.id))
    store_seconds = time.perf_counter() - start_store

    start_retrieve = time.perf_counter()
    pack = builder.build(domain="health", query="benchmark", limit=50)
    retrieve_seconds = time.perf_counter() - start_retrieve

    target_id = "event:bench:0"
    start_delete = time.perf_counter()
    proof = engine.delete_and_recompute(target_id, "event", reason="benchmark")
    delete_seconds = time.perf_counter() - start_delete

    metrics = {
        "event_count": 1000,
        "store_seconds": store_seconds,
        "retrieve_seconds": retrieve_seconds,
        "delete_seconds": delete_seconds,
        "health_fact_count": len(pack.to_dict().get("facts", [])),
        "deletion_verified": bool(proof.checks.get("deletion_verified", False)),
    }

    out_path = workspace_tmp_path / "benchmark_results.json"
    out_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    optional_artifact_path = os.environ.get("LORE_BENCHMARK_ARTIFACT_PATH", "").strip()
    if optional_artifact_path:
        Path(optional_artifact_path).write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print("benchmark:", json.dumps(metrics))

    assert metrics["event_count"] == 1000
    assert metrics["deletion_verified"] is True
    assert metrics["store_seconds"] < 30
    assert metrics["retrieve_seconds"] < 5
    assert metrics["delete_seconds"] < 10
