import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_workspace_tmp_path_is_outside_repo(workspace_tmp_path):
    # conftest creates test workspaces in OS temp (tempfile.mkdtemp), so they
    # are always outside the repo tree and require no .gitignore coverage.
    assert not str(workspace_tmp_path).startswith(str(REPO_ROOT))
