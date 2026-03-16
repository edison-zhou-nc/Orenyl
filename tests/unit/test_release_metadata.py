from pathlib import Path

import lore

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_release_metadata_targets_rc1() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text()

    assert 'version = "1.0.0rc1"' in pyproject
    assert "[project.urls]" in pyproject
    assert "Homepage" in pyproject
    assert "Repository" in pyproject
    assert "Changelog" in pyproject
    assert lore.__version__ == "1.0.0rc1"
