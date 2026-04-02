from __future__ import annotations

import sys

from lore.release_verify import run_release_verification

if __name__ == "__main__":
    raise SystemExit(run_release_verification(sys.executable))
