#!/usr/bin/env python3
# ruff: noqa: E402, I001
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
os.chdir(REPO_ROOT)

from lore.release_verify import build_release_commands, run_release_commands


if __name__ == "__main__":
    raise SystemExit(run_release_commands(build_release_commands(sys.executable)))
