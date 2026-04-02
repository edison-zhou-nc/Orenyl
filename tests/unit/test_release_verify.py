from lore.release_verify import build_release_commands, run_release_commands


def test_build_release_commands_covers_current_release_gate_in_order() -> None:
    commands = build_release_commands("python")

    flattened = [" ".join(command) for command in commands]
    assert any("ruff check . --select F,B" in command for command in flattened)
    assert any("ruff check src --select S105,S324,S603,S607,S608" in command for command in flattened)
    assert any("bandit -r src/lore -ll -q" in command for command in flattened)
    assert any("pip_audit -r requirements.lock --disable-pip" in command for command in flattened)
    assert any("pip_audit -r requirements-dev.lock --disable-pip" in command for command in flattened)
    assert any("mypy src/lore --config-file pyproject.toml" in command for command in flattened)
    assert any("pytest tests/unit tests/integration -q --cov=src/lore --cov-report=term-missing --cov-fail-under=80" in command for command in flattened)
    assert any("pytest tests/unit/test_health_structured.py tests/integration/test_perf_regression.py tests/integration/test_server_metrics_and_health.py -q" in command for command in flattened)
    assert any("pytest tests/integration/test_phase3_tool_isolation.py tests/integration/test_federation_worker_idempotency.py tests/integration/test_federation_conflict_resolution.py tests/unit/test_sync_envelope_validation.py tests/integration/test_sync_journal_persistence.py -q" in command for command in flattened)
    assert any(command == "python -m build" for command in flattened)
    assert ["python", "-c", "import lore, lore.server; print('ok')"] in commands
    assert len(commands) == 11


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
