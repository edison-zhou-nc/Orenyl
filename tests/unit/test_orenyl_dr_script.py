from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def test_orenyl_dr_uses_orenyl_defaults(monkeypatch):
    captured: dict[str, object] = {}

    class _Database:
        def __init__(self, db_path: str):
            captured["db_path"] = db_path

    class _DRService:
        def __init__(self, db, db_path: str, snapshot_dir: str):
            captured["service_db"] = db
            captured["service_db_path"] = db_path
            captured["snapshot_dir"] = snapshot_dir

        def create_snapshot(self, label: str):  # pragma: no cover - not exercised
            return {"label": label}

        def verify_snapshot(self, snapshot_id: str):  # pragma: no cover - not exercised
            return {"snapshot_id": snapshot_id}

        def restore_snapshot(self, snapshot_id: str):  # pragma: no cover - not exercised
            return {"snapshot_id": snapshot_id}

    monkeypatch.delenv("ORENYL_DB_PATH", raising=False)
    monkeypatch.delenv("ORENYL_DR_SNAPSHOT_DIR", raising=False)
    monkeypatch.setattr("orenyl.db.Database", _Database)
    monkeypatch.setattr("orenyl.disaster_recovery.DRService", _DRService)

    script_path = Path(__file__).resolve().parents[2] / "scripts" / "orenyl_dr.py"
    spec = importlib.util.spec_from_file_location("orenyl_dr_test_module", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
        service = module._build_service()
    finally:
        sys.modules.pop(spec.name, None)

    assert captured["db_path"] == "orenyl_memory.db"
    assert captured["service_db_path"] == "orenyl_memory.db"
    assert captured["snapshot_dir"] == "orenyl_snapshots"
    assert service is not None
