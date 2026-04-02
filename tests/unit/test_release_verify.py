from lore.release_verify import build_release_commands, run_release_commands


def test_build_release_commands_covers_current_release_gate() -> None:
    commands = build_release_commands("python")

    flattened = [" ".join(command) for command in commands]
    assert any("ruff check . --select F,B" in command for command in flattened)
    assert any("ruff check src --select S105,S324,S603,S607,S608" in command for command in flattened)
    assert any("bandit -r src/lore -ll -q" in command for command in flattened)
    assert any("pip_audit -r requirements.lock --disable-pip" in command for command in flattened)
    assert any("mypy src/lore --config-file pyproject.toml" in command for command in flattened)
    assert any("--cov=src/lore" in command for command in flattened)
    assert any("python -m build" in command for command in flattened)


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

    monkeypatch.setattr("subprocess.run", fake_run)
    exit_code = run_release_commands([["one"], ["two"], ["three"]])

    assert exit_code == 1
    assert calls == [["one"], ["two"]]
