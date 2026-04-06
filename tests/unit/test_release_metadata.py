"""Release metadata checks for packaging and public launch signals."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_release_metadata_matches_public_launch_positioning() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text()

    assert 'version = "1.0.0"' in pyproject
    assert 'name = "orenyl-mcp-server"' in pyproject
    assert 'name = "lore-mcp-server"' not in pyproject
    assert 'orenyl-server = "orenyl.server:main"' in pyproject
    assert "lore-server" not in pyproject
    assert "[project.urls]" in pyproject
    assert "Homepage" in pyproject
    assert "Repository" in pyproject
    assert "Changelog" in pyproject
    assert "Development Status :: 4 - Beta" in pyproject
    assert "Development Status :: 5 - Production/Stable" not in pyproject
    assert "Compliance-grade memory MCP server" not in pyproject


def test_release_metadata_does_not_mix_license_expression_and_classifier() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text()

    assert 'license = "Apache-2.0"' in pyproject
    assert "License :: OSI Approved :: Apache Software License" not in pyproject
