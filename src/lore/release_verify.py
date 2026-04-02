from __future__ import annotations

import subprocess
import sys


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
        [py, "-c", "import lore, lore.server; print('ok')"],
        _build_fresh_venv_smoke_command(py),
    ]


def _build_fresh_venv_smoke_command(python_bin: str) -> list[str]:
    return [python_bin, "-c", _build_fresh_venv_smoke_script()]


def _build_fresh_venv_smoke_script() -> str:
    return "\n".join(
        [
            "import subprocess",
            "import sys",
            "import tempfile",
            "import venv",
            "from pathlib import Path",
            "",
            'wheels = sorted(Path("dist").glob("*.whl"))',
            'if not wheels:',
            '    raise FileNotFoundError("No built wheel found in dist/")',
            "",
            'with tempfile.TemporaryDirectory(prefix="lore-release-smoke-") as temp_dir:',
            "    venv_dir = Path(temp_dir)",
            "    venv.EnvBuilder(with_pip=True).create(venv_dir)",
            '    bin_dir = venv_dir / ("Scripts" if sys.platform == "win32" else "bin")',
            '    python_path = bin_dir / ("python.exe" if sys.platform == "win32" else "python")',
            '    subprocess.run([str(python_path), "-m", "pip", "install", "--upgrade", "pip"], check=True)',
            '    subprocess.run([str(python_path), "-m", "pip", "install", str(wheels[0])], check=True)',
            '    subprocess.run([str(python_path), "-c", "import lore, lore.server; print(\'ok\')"], check=True)',
        ]
    )


def run_release_commands(commands: list[list[str]]) -> int:
    for command in commands:
        completed = subprocess.run(command, check=False)  # noqa: S603
        if completed.returncode:
            return completed.returncode
    return 0
