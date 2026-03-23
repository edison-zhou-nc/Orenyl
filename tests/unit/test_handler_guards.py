from pathlib import Path


def test_store_event_uses_runtime_guard_instead_of_assert() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    source = (repo_root / "src" / "lore" / "handlers" / "core.py").read_text(encoding="utf-8")

    assert "assert encryption_material is not None" not in source
