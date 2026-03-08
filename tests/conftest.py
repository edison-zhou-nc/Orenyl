import sys
import shutil
import uuid
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))


@pytest.fixture
def workspace_tmp_path():
    base = REPO_ROOT / "tests" / ".tmp"
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"pytest-{uuid.uuid4().hex[:8]}"
    path.mkdir(parents=True, exist_ok=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture(autouse=True)
def _reset_server_runtime_state():
    try:
        from lore import server
    except Exception:
        yield
        return
    reset = getattr(server, "_reset_runtime_state_for_tests", None)
    if callable(reset):
        reset()
    yield
