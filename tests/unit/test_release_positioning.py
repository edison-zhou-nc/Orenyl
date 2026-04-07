"""Verify release positioning is consistent across all public-facing files."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_pyproject_classifies_as_beta() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "Development Status :: 4 - Beta" in pyproject
    assert "Development Status :: 5 - Production/Stable" not in pyproject


def test_changelog_does_not_claim_production_stable() -> None:
    changelog = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert "production/stable" not in changelog.lower()


def test_release_process_does_not_claim_ga() -> None:
    doc = (REPO_ROOT / "docs" / "RELEASE_PROCESS.md").read_text(encoding="utf-8")

    assert "treat tags as release candidates" not in doc.lower()


def test_readme_scopes_release_honestly() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    assert "not yet" in readme.lower() or "not externally certified" in readme.lower()
    assert "enterprise-certified" not in readme.lower()
    assert "production-grade ga" not in readme.lower()


def test_readme_describes_early_production_without_claiming_enterprise_ga() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8").lower()

    assert "orenyl is in early production / public beta." in readme
    assert "enterprise-complete" in readme
    assert "enterprise certified" not in readme
