import shutil
import sys
import tempfile
import uuid
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
while str(SRC_ROOT) in sys.path:
    sys.path.remove(str(SRC_ROOT))
sys.path.insert(0, str(SRC_ROOT))


@pytest.fixture
def workspace_tmp_path():
    path = Path(tempfile.mkdtemp(prefix=f"orenyl-pytest-{uuid.uuid4().hex[:8]}-"))
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture(autouse=True)
def _reset_server_runtime_state(workspace_tmp_path, monkeypatch):
    db_path = workspace_tmp_path / "orenyl_memory.db"
    audit_db_path = workspace_tmp_path / "orenyl_audit.db"
    snapshot_dir = workspace_tmp_path / "orenyl_snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("ORENYL_DB_PATH", str(db_path))
    monkeypatch.setenv("ORENYL_AUDIT_DB_PATH", str(audit_db_path))
    monkeypatch.setenv("ORENYL_DR_SNAPSHOT_DIR", str(snapshot_dir))
    monkeypatch.setenv("ORENYL_TESTING_MODE", "1")

    server = sys.modules.get("orenyl.server")
    audit = sys.modules.get("orenyl.audit")
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
        monkeypatch.setenv("ORENYL_TESTING_MODE", "1")
        server = sys.modules.get("orenyl.server")
        audit = sys.modules.get("orenyl.audit")
        rebind = getattr(server, "_rebind_runtime_state_for_tests", None) if server else None
        reset = getattr(server, "_reset_runtime_state_for_tests", None) if server else None
        reset_audit = getattr(audit, "_reset_for_tests", None) if audit else None
        if callable(rebind):
            rebind(":memory:")
        if callable(reset):
            reset()
        if callable(reset_audit):
            reset_audit()
