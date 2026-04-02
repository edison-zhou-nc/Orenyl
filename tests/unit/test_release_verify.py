from lore.release_verify import build_release_commands, build_smoke_install_commands
from scripts.verify_release import run_release_commands


def test_build_release_commands_covers_current_release_gate_in_order() -> None:
    commands = build_release_commands("python")

    assert commands == [
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
    ]


def test_build_smoke_install_commands_uses_fresh_venv_python() -> None:
    commands = build_smoke_install_commands("venv-python", "dist/lore-1.2.3-py3-none-any.whl")

    assert commands == [
        ["venv-python", "-m", "pip", "install", "--upgrade", "pip"],
        ["venv-python", "-m", "pip", "install", "dist/lore-1.2.3-py3-none-any.whl"],
        ["venv-python", "-c", "import lore, lore.server"],
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

    monkeypatch.setattr("scripts.verify_release.subprocess.run", fake_run)
    exit_code = run_release_commands([["one"], ["two"], ["three"]])

    assert exit_code == 1
    assert calls == [["one"], ["two"]]
