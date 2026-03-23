from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_release_workflow_runs_verification_before_publish() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "release.yml").read_text()

    assert "python -m ruff check" in workflow
    assert "python -m mypy src/lore --config-file pyproject.toml" in workflow
    assert "python -m pytest tests/unit tests/integration -q --cov=src/lore" in workflow
    assert "python -m build" in workflow
    assert "import lore, lore.server" in workflow


def test_dev_requirements_include_release_verification_tools() -> None:
    requirements_dev = (REPO_ROOT / "requirements-dev.txt").read_text()

    assert "mypy==" in requirements_dev
    assert "build==" in requirements_dev
