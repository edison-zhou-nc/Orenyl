from __future__ import annotations

import subprocess
import sys
import tempfile
import venv
from pathlib import Path


def build_release_commands(python_bin: str | None = None) -> list[list[str]]:
    py = python_bin or sys.executable
    return [
        [py, "-m", "ruff", "check", ".", "--select", "F,B"],
        [py, "-m", "ruff", "check", "src", "--select", "S105,S324,S603,S607,S608"],
        [py, "-m", "bandit", "-r", "src/lore", "-ll", "-q"],
        [py, "-m", "pip_audit", "-r", "requirements.lock", "--disable-pip"],
        [py, "-m", "pip_audit", "-r", "requirements-dev.lock", "--disable-pip"],
        [py, "-m", "mypy", "src/lore", "--config-file", "pyproject.toml"],
        [
            py,
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
            py,
            "-m",
            "pytest",
            "tests/unit/test_health_structured.py",
            "tests/integration/test_perf_regression.py",
            "tests/integration/test_server_metrics_and_health.py",
            "-q",
        ],
        [
            py,
            "-m",
            "pytest",
            "tests/integration/test_phase3_tool_isolation.py",
            "tests/integration/test_federation_worker_idempotency.py",
            "tests/integration/test_federation_conflict_resolution.py",
            "tests/unit/test_sync_envelope_validation.py",
            "tests/integration/test_sync_journal_persistence.py",
            "-q",
        ],
        [py, "-m", "build"],
    ]


def build_smoke_install_commands(python_bin: str, wheel_path: str) -> list[list[str]]:
    return [
        [python_bin, "-m", "pip", "install", "--upgrade", "pip"],
        [python_bin, "-m", "pip", "install", wheel_path],
        [python_bin, "-c", "import lore, lore.server"],
    ]


def run_release_commands(commands: list[list[str]]) -> int:
    for command in commands:
        completed = subprocess.run(command, check=False)  # noqa: S603
        if completed.returncode:
            return completed.returncode
    return 0


def find_built_wheel() -> str:
    wheels = sorted(Path("dist").glob("*.whl"))
    if not wheels:
        raise FileNotFoundError("No built wheel found in dist/")
    return str(wheels[0])


def run_smoke_install_commands(wheel_path: str) -> int:
    with tempfile.TemporaryDirectory(prefix="lore-release-smoke-") as temp_dir:
        venv_dir = Path(temp_dir)
        venv.EnvBuilder(with_pip=True).create(venv_dir)
        python_bin = venv_dir / ("Scripts" if sys.platform == "win32" else "bin")
        python_path = python_bin / ("python.exe" if sys.platform == "win32" else "python")
        return run_release_commands(build_smoke_install_commands(str(python_path), wheel_path))


def run_release_verification(python_bin: str | None = None) -> int:
    release_exit_code = run_release_commands(build_release_commands(python_bin))
    if release_exit_code:
        return release_exit_code
    return run_smoke_install_commands(find_built_wheel())
