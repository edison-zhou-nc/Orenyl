import shutil
import sys
import tempfile
import uuid
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))


@pytest.fixture
def workspace_tmp_path():
    path = Path(tempfile.mkdtemp(prefix=f"lore-pytest-{uuid.uuid4().hex[:8]}-"))
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture(autouse=True)
def _reset_server_runtime_state(workspace_tmp_path, monkeypatch):
    db_path = workspace_tmp_path / "lore_memory.db"
    audit_db_path = workspace_tmp_path / "lore_audit.db"
    snapshot_dir = workspace_tmp_path / "lore_snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("LORE_DB_PATH", str(db_path))
    monkeypatch.setenv("LORE_AUDIT_DB_PATH", str(audit_db_path))
    monkeypatch.setenv("LORE_DR_SNAPSHOT_DIR", str(snapshot_dir))

    server = sys.modules.get("lore.server")
    audit = sys.modules.get("lore.audit")
    rebind = getattr(server, "_rebind_runtime_state_for_tests", None) if server else None
    reset = getattr(server, "_reset_runtime_state_for_tests", None) if server else None
    reset_audit = getattr(audit, "_reset_for_tests", None) if audit else None
    if callable(rebind):
        rebind()
    if callable(reset):
        reset()
    if callable(reset_audit):
        reset_audit()
    try:
        yield
    finally:
        server = sys.modules.get("lore.server")
        audit = sys.modules.get("lore.audit")
        rebind = getattr(server, "_rebind_runtime_state_for_tests", None) if server else None
        reset = getattr(server, "_reset_runtime_state_for_tests", None) if server else None
        reset_audit = getattr(audit, "_reset_for_tests", None) if audit else None
        if callable(rebind):
            rebind(":memory:")
        if callable(reset):
            reset()
        if callable(reset_audit):
            reset_audit()
