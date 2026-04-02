# ruff: noqa: I001
from __future__ import annotations

import sys

from lore.release_verify import build_release_commands, run_release_commands


if __name__ == "__main__":
    raise SystemExit(run_release_commands(build_release_commands(sys.executable)))
