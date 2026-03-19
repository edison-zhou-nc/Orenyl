"""GA release metadata checks for packaging and published version signals."""

from pathlib import Path

import lore

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_release_metadata_targets_ga() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text()

    assert 'version = "1.0.0"' in pyproject
    assert "[project.urls]" in pyproject
    assert "Homepage" in pyproject
    assert "Repository" in pyproject
    assert "Changelog" in pyproject
    assert "Development Status :: 5 - Production/Stable" in pyproject
    assert lore.__version__ == "1.0.0"


def test_release_metadata_does_not_mix_license_expression_and_classifier() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text()

    assert 'license = "Apache-2.0"' in pyproject
    assert "License :: OSI Approved :: Apache Software License" not in pyproject
