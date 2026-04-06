from lore.release_verify import _build_wheel_smoke_script, build_release_commands, run_release_commands


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
        ["python", "-m", "build"],
        ["python", "-c", _build_wheel_smoke_script()],
    ]
    assert sum(command[1:3] == ["-m", "pytest"] for command in commands) == 1


def test_build_wheel_smoke_script_cleans_up_temp_env() -> None:
    script = _build_wheel_smoke_script()

    assert "tempfile.mkdtemp" in script
    assert "shutil.rmtree" in script
    assert "finally:" in script


def test_run_release_commands_stops_on_first_failure(monkeypatch) -> None:
    calls: list[list[str]] = []

    class Result:
        def __init__(self, returncode: int) -> None:
            self.returncode = returncode

    def fake_run(command, *, check):
        assert check is False
        calls.append(command)
        if len(calls) == 2:
            return Result(1)
        return Result(0)

    monkeypatch.setattr("lore.release_verify.subprocess.run", fake_run)
    exit_code = run_release_commands([["one"], ["two"], ["three"]])

    assert exit_code == 1
    assert calls == [["one"], ["two"]]
