from __future__ import annotations

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
    ]


def build_smoke_install_commands(python_bin: str, wheel_path: str) -> list[list[str]]:
    return [
        [python_bin, "-m", "pip", "install", "--upgrade", "pip"],
        [python_bin, "-m", "pip", "install", wheel_path],
        [python_bin, "-c", "import lore, lore.server"],
    ]
