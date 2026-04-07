from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_release_workflow_runs_verification_before_publish() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    assert "python -m ruff check" in workflow
    assert "python -m bandit -r src/orenyl -ll -q" in workflow
    assert "python -m mypy src/orenyl --config-file pyproject.toml" in workflow
    assert "python -m pytest tests/unit tests/integration -q --cov=src/orenyl" in workflow
    assert "python -m build" in workflow
    assert 'python -c "import orenyl, orenyl.server"' in workflow
    assert "python -m pip install -r requirements.lock" in workflow
    assert "python -m pip install -r requirements-dev.lock" in workflow
    assert "python -m pip install dist/*.whl" in workflow
    assert ".venv-smoke/bin/activate" in workflow
    assert "name: orenyl-dist" in workflow
    assert "python -m orenyl.server" not in workflow
    assert "python -m pip install build pytest pytest-cov mypy bandit pip-audit" not in workflow


def test_dev_requirements_include_release_verification_tools() -> None:
    requirements_dev = (REPO_ROOT / "requirements-dev.txt").read_text(encoding="utf-8")

    assert "mypy==" in requirements_dev
    assert "build==" in requirements_dev
    assert "bandit==" in requirements_dev
    assert "pip-audit==" in requirements_dev
    assert "pytest-cov==" in requirements_dev


def test_dev_lockfile_includes_release_verification_tools() -> None:
    requirements_dev_lock = (REPO_ROOT / "requirements-dev.lock").read_text(encoding="utf-8")

    assert "mypy==" in requirements_dev_lock
    assert "build==" in requirements_dev_lock
    assert "bandit==" in requirements_dev_lock
    assert "pip-audit==" in requirements_dev_lock
    assert "pytest-cov==" in requirements_dev_lock
