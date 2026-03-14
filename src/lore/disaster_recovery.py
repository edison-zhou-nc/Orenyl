"""Disaster recovery snapshot helpers."""

from __future__ import annotations

import hashlib
import shutil
import sqlite3
import uuid
from pathlib import Path

from .db import Database
from .models import DRSnapshot


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


class DRService:
    def __init__(self, db: Database, db_path: str, snapshot_dir: str):
        self.db = db
        self.db_path = Path(db_path)
        self.snapshot_dir = Path(snapshot_dir)

    def create_snapshot(self, label: str, tenant_id: str = "default") -> dict:
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        snapshot_id = f"snapshot:{label}:{uuid.uuid4().hex[:12]}"
        snapshot_file = self.snapshot_dir / f"{snapshot_id.replace(':', '_')}.db"
        self.db.conn.execute("PRAGMA wal_checkpoint(FULL)")
        self.db.conn.commit()
        shutil.copy2(self.db_path, snapshot_file)
        checksum = _sha256_file(snapshot_file)
        self.db.insert_dr_snapshot(
            DRSnapshot(
                snapshot_id=snapshot_id,
                tenant_id=tenant_id or "default",
                checksum=checksum,
                storage_uri=str(snapshot_file),
            )
        )
        return {
            "ok": True,
            "snapshot_id": snapshot_id,
            "storage_uri": str(snapshot_file),
            "checksum": checksum,
        }

    def verify_snapshot(self, snapshot_id: str, tenant_id: str = "default") -> dict:
        snapshot = self.db.get_dr_snapshot(snapshot_id=snapshot_id, tenant_id=tenant_id)
        if snapshot is None:
            return {"ok": False, "error": "snapshot_not_found"}
        path = Path(str(snapshot["storage_uri"]))
        if not path.exists():
            return {"ok": False, "error": "snapshot_missing", "snapshot_id": snapshot_id}
        actual = _sha256_file(path)
        expected = str(snapshot["checksum"])
        return {
            "ok": actual == expected,
            "snapshot_id": snapshot_id,
            "expected_checksum": expected,
            "actual_checksum": actual,
        }

    def restore_snapshot(self, snapshot_id: str, tenant_id: str = "default") -> dict:
        snapshot = self.db.get_dr_snapshot(snapshot_id=snapshot_id, tenant_id=tenant_id)
        if snapshot is None:
            return {"ok": False, "error": "snapshot_not_found"}
        snapshot_path = Path(str(snapshot["storage_uri"]))
        if not snapshot_path.exists():
            return {"ok": False, "error": "snapshot_missing", "snapshot_id": snapshot_id}
        expected_checksum = str(snapshot["checksum"])
        actual_checksum = _sha256_file(snapshot_path)
        if actual_checksum != expected_checksum:
            return {
                "ok": False,
                "error": "snapshot_checksum_mismatch",
                "snapshot_id": snapshot_id,
                "expected_checksum": expected_checksum,
                "actual_checksum": actual_checksum,
            }
        backup_path = self.db_path.with_suffix(f"{self.db_path.suffix}.pre_restore.bak")
        self.db.conn.commit()
        if self.db_path.exists():
            shutil.copy2(self.db_path, backup_path)
        with sqlite3.connect(snapshot_path) as source_conn:
            source_conn.backup(self.db.conn)
        self.db.conn.commit()
        return {
            "ok": True,
            "snapshot_id": snapshot_id,
            "restored_to": str(self.db_path),
            "backup_path": str(backup_path) if backup_path.exists() else "",
        }
