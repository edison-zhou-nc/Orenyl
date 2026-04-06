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
        [py, "-m", "build"],
        [py, "-c", _build_wheel_smoke_script()],
    ]


def run_release_commands(commands: list[list[str]]) -> int:
    for command in commands:
        completed = subprocess.run(command, check=False)  # noqa: S603
        if completed.returncode:
            return completed.returncode
    return 0


def _build_wheel_smoke_script() -> str:
    return "\n".join(
        [
            "import pathlib",
            "import shutil",
            "import subprocess",
            "import sys",
            "import tempfile",
            "import venv",
            "",
            "dist = pathlib.Path('dist')",
            "wheel = next(dist.glob('lore_mcp-*.whl'))",
            "venv_dir = pathlib.Path(tempfile.mkdtemp(prefix='lore-smoke-'))",
            "try:",
            "    venv.EnvBuilder(with_pip=True).create(venv_dir)",
            "    scripts = venv_dir / ('Scripts' if sys.platform == 'win32' else 'bin')",
            "    python_bin = scripts / ('python.exe' if sys.platform == 'win32' else 'python')",
            "    subprocess.run([str(python_bin), '-m', 'pip', 'install', '--upgrade', 'pip'], check=True)",
            "    subprocess.run([str(python_bin), '-m', 'pip', 'install', str(wheel)], check=True)",
            "    subprocess.run([str(python_bin), '-c', 'import lore, lore.server'], check=True)",
            "finally:",
            "    shutil.rmtree(venv_dir, ignore_errors=True)",
        ]
    )
