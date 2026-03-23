from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_public_repo_trust_docs_exist() -> None:
    assert (REPO_ROOT / "SECURITY.md").exists()
    assert (REPO_ROOT / "CODE_OF_CONDUCT.md").exists()


def test_governance_and_contributing_link_to_trust_docs() -> None:
    governance = (REPO_ROOT / "GOVERNANCE.md").read_text()
    contributing = (REPO_ROOT / "CONTRIBUTING.md").read_text()

    assert "SECURITY.md" in governance or "SECURITY.md" in contributing
    assert "CODE_OF_CONDUCT.md" in governance or "CODE_OF_CONDUCT.md" in contributing


def test_contributing_lists_launch_validation_commands() -> None:
    contributing = (REPO_ROOT / "CONTRIBUTING.md").read_text()

    assert "python -m pytest -q" in contributing
    assert "python -m ruff check . --select F,B" in contributing
    assert "python -m mypy src/lore --config-file pyproject.toml" in contributing
    assert "python -m build" in contributing


def test_gitignore_covers_local_build_artifacts() -> None:
    gitignore = (REPO_ROOT / ".gitignore").read_text()

    assert "dist/" in gitignore
    assert "dist_fix/" in gitignore
