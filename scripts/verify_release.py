from __future__ import annotations

import subprocess
import sys
import tempfile
import venv
from pathlib import Path

from lore.release_verify import build_release_commands, build_smoke_install_commands


def run_release_commands(commands: list[list[str]]) -> int:
    for command in commands:
        completed = subprocess.run(command, check=False)
        if completed.returncode:
            return completed.returncode
    return 0


def run_smoke_install_commands(wheel_path: str) -> int:
    with tempfile.TemporaryDirectory(prefix="lore-release-smoke-") as temp_dir:
        venv_dir = Path(temp_dir)
        venv.EnvBuilder(with_pip=True).create(venv_dir)
        python_bin = venv_dir / ("Scripts" if sys.platform == "win32" else "bin")
        python_path = python_bin / ("python.exe" if sys.platform == "win32" else "python")
        return run_release_commands(build_smoke_install_commands(str(python_path), wheel_path))


def find_built_wheel() -> str:
    wheels = sorted(Path("dist").glob("*.whl"))
    if not wheels:
        raise FileNotFoundError("No built wheel found in dist/")
    return str(wheels[0])


if __name__ == "__main__":
    release_exit_code = run_release_commands(build_release_commands(sys.executable))
    if release_exit_code:
        raise SystemExit(release_exit_code)
    raise SystemExit(run_smoke_install_commands(find_built_wheel()))
