from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from orenyl import env_vars
from orenyl.db import Database
from orenyl.disaster_recovery import DRService


def _build_service() -> DRService:
    db_path = os.environ.get(env_vars.DB_PATH, "lore_memory.db")
    snapshot_dir = os.environ.get(env_vars.DR_SNAPSHOT_DIR, "lore_snapshots")
    db = Database(db_path)
    return DRService(db=db, db_path=db_path, snapshot_dir=snapshot_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="orenyl disaster recovery operations.")
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create", help="Create snapshot")
    create.add_argument("--label", default="manual")

    verify = sub.add_parser("verify", help="Verify snapshot checksum")
    verify.add_argument("snapshot_id")

    restore = sub.add_parser("restore", help="Restore snapshot")
    restore.add_argument("snapshot_id")

    args = parser.parse_args()
    service = _build_service()
    if args.command == "create":
        out = service.create_snapshot(label=args.label)
    elif args.command == "verify":
        out = service.verify_snapshot(snapshot_id=args.snapshot_id)
    else:
        out = service.restore_snapshot(snapshot_id=args.snapshot_id)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
