import runpy
import sys
from pathlib import Path

import pytest

from lore.release_verify import build_release_commands, run_release_commands


def test_build_release_commands_covers_current_release_gate_in_order() -> None:
    assert build_release_commands("python") == [
        ["python", "-m", "ruff", "check", ".", "--select", "F,B"],
        ["python", "-m", "ruff", "check", "src", "--select", "S105,S324,S603,S607,S608"],
        ["python", "-m", "bandit", "-r", "src/lore", "-ll", "-q"],
        ["python", "-m", "pip_audit", "-r", "requirements.lock", "--disable-pip"],
        ["python", "-m", "pip_audit", "-r", "requirements-dev.lock", "--disable-pip"],
        ["python", "-m", "mypy", "src/lore", "--config-file", "pyproject.toml"],
        [
            "python",
            "-m",
            "pytest",
            "tests/unit",
            "tests/integration",
            "-q",
            "--cov=src/lore",
            "--cov-report=term-missing",
            "--cov-fail-under=80",
        ],
        [
            "python",
            "-m",
            "pytest",
            "tests/unit/test_health_structured.py",
            "tests/integration/test_perf_regression.py",
            "tests/integration/test_server_metrics_and_health.py",
            "-q",
        ],
        [
            "python",
            "-m",
            "pytest",
            "tests/integration/test_phase3_tool_isolation.py",
            "tests/integration/test_federation_worker_idempotency.py",
            "tests/integration/test_federation_conflict_resolution.py",
            "tests/unit/test_sync_envelope_validation.py",
            "tests/integration/test_sync_journal_persistence.py",
            "-q",
        ],
        ["python", "-m", "build"],
        ["python", "-c", "import lore, lore.server; print('ok')"],
    ]


def test_run_release_commands_stops_on_first_failure(monkeypatch) -> None:
    calls: list[list[str]] = []

    class Result:
        def __init__(self, returncode: int) -> None:
            self.returncode = returncode

    def fake_run(command, check):
        calls.append(command)
        if len(calls) == 2:
            return Result(1)
        return Result(0)

    monkeypatch.setattr("lore.release_verify.subprocess.run", fake_run)
    exit_code = run_release_commands([["one"], ["two"], ["three"]])

    assert exit_code == 1
    assert calls == [["one"], ["two"]]


def test_verify_release_anchors_to_repo_root(monkeypatch, tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "verify_release.py"
    observed: dict[str, Path | list[list[str]] | str] = {}

    def fake_build_release_commands(python_bin: str | None = None):
        observed["python_bin"] = python_bin
        return [["python", "-c", "pass"]]

    def fake_run_release_commands(commands):
        observed["cwd"] = Path.cwd()
        observed["commands"] = commands
        return 0

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("lore.release_verify.build_release_commands", fake_build_release_commands)
    monkeypatch.setattr("lore.release_verify.run_release_commands", fake_run_release_commands)

    with pytest.raises(SystemExit) as exc_info:
        runpy.run_path(str(script_path), run_name="__main__")

    assert exc_info.value.code == 0
    assert observed["python_bin"] == sys.executable
    assert observed["cwd"] == repo_root
    assert observed["commands"] == [["python", "-c", "pass"]]
