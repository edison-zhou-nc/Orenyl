import json
import os
from pathlib import Path

from scripts.run_benchmarks import baseline_artifact_metrics


def test_scale_benchmark_generates_baseline_artifact(workspace_tmp_path):
    metrics = baseline_artifact_metrics(1000)

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
