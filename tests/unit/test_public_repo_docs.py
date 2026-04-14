from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_public_repo_trust_docs_exist() -> None:
    assert (REPO_ROOT / "SECURITY.md").exists()
    assert (REPO_ROOT / "CODE_OF_CONDUCT.md").exists()


def test_trust_docs_do_not_reference_the_old_lore_brand_contact_domain() -> None:
    security = (REPO_ROOT / "SECURITY.md").read_text(encoding="utf-8")
    conduct = (REPO_ROOT / "CODE_OF_CONDUCT.md").read_text(encoding="utf-8")

    assert "@loremcp.com" not in security
    assert "@loremcp.com" not in conduct
    assert "github.com/edison-zhou-nc" in security
    assert "github.com/edison-zhou-nc" in conduct


def test_governance_and_contributing_link_to_trust_docs() -> None:
    governance = (REPO_ROOT / "GOVERNANCE.md").read_text()
    contributing = (REPO_ROOT / "CONTRIBUTING.md").read_text()

    assert "SECURITY.md" in governance or "SECURITY.md" in contributing
    assert "CODE_OF_CONDUCT.md" in governance or "CODE_OF_CONDUCT.md" in contributing


def test_contributing_lists_release_validation_commands() -> None:
    contributing = (REPO_ROOT / "CONTRIBUTING.md").read_text()

    assert "release-readiness" in contributing
    assert "launch-readiness" not in contributing
    assert "python -m pytest -q" in contributing
    assert "python -m ruff check . --select F,B" in contributing
    assert "python -m mypy src/orenyl --config-file pyproject.toml" in contributing
    assert "python -m build" in contributing


def test_gitignore_covers_local_build_artifacts() -> None:
    gitignore = (REPO_ROOT / ".gitignore").read_text()

    assert "dist/" in gitignore
    assert "dist_fix/" in gitignore
