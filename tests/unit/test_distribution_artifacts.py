from pathlib import Path


def test_distribution_artifacts_exist():
    assert Path("scripts/demo_v2.py").exists()
    assert Path("docs/benchmarks/v2-baseline.md").exists()
