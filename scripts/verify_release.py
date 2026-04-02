#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

from lore.release_verify import build_release_commands, run_release_commands

REPO_ROOT = Path(__file__).resolve().parents[1]


if __name__ == "__main__":
    os.chdir(REPO_ROOT)
    raise SystemExit(run_release_commands(build_release_commands(sys.executable)))
