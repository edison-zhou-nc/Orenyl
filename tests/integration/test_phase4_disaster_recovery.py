from __future__ import annotations

import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest

from lore.db import Database
from lore.disaster_recovery import DRService
from lore.models import Event


def test_snapshot_and_verify_round_trip(tmp_path):
    db_path = tmp_path / "lore.db"
    db = Database(str(db_path))
    db.insert_event(
        Event(
            id="event:test:dr-1",
            type="note",
            payload={"text": "before snapshot"},
            domains=["general"],
        )
    )

    dr = DRService(db=db, db_path=str(db_path), snapshot_dir=str(tmp_path / "snapshots"))
    snapshot = dr.create_snapshot(label="baseline")
    snapshot_file = Path(db.get_dr_snapshot(snapshot["snapshot_id"])["storage_uri"])

    assert snapshot_file.exists()
    assert snapshot["checksum"]
    assert "storage_uri" not in snapshot
    verify = dr.verify_snapshot(snapshot["snapshot_id"])
    assert verify["ok"] is True


def test_restore_snapshot_recovers_previous_db_state(tmp_path):
    db_path = tmp_path / "lore.db"
    db = Database(str(db_path))
    dr = DRService(db=db, db_path=str(db_path), snapshot_dir=str(tmp_path / "snapshots"))

    db.insert_event(
        Event(
            id="event:test:dr-restore-before",
            type="note",
            payload={"text": "before"},
            domains=["general"],
        )
    )
    snapshot = dr.create_snapshot(label="restore")
    db.insert_event(
        Event(
            id="event:test:dr-restore-after",
            type="note",
            payload={"text": "after"},
            domains=["general"],
        )
    )

    restored = dr.restore_snapshot(snapshot["snapshot_id"])
    assert restored["ok"] is True

    reloaded = Database(str(db_path))
    assert reloaded.get_event("event:test:dr-restore-before") is not None
    assert reloaded.get_event("event:test:dr-restore-after") is None


def test_restore_snapshot_succeeds_with_open_destination_transaction(tmp_path):
    db_path = tmp_path / "lore.db"
    db = Database(str(db_path))
    dr = DRService(db=db, db_path=str(db_path), snapshot_dir=str(tmp_path / "snapshots"))

    db.insert_event(
        Event(
            id="event:test:dr-open-tx-before",
            type="note",
            payload={"text": "before"},
            domains=["general"],
        )
    )
    snapshot = dr.create_snapshot(label="restore-open-tx")

    with db.transaction():
        db.insert_event(
            Event(
                id="event:test:dr-open-tx-pending",
                type="note",
                payload={"text": "pending"},
                domains=["general"],
            )
        )
        restored = dr.restore_snapshot(snapshot["snapshot_id"])
        assert restored["ok"] is True

    reloaded = Database(str(db_path))
    assert reloaded.get_event("event:test:dr-open-tx-before") is not None
    assert reloaded.get_event("event:test:dr-open-tx-pending") is None


def test_restore_snapshot_closes_source_connection(monkeypatch, tmp_path):
    class TrackingConnection(sqlite3.Connection):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.closed = False

        def close(self):
            self.closed = True
            return super().close()

    original_connect = sqlite3.connect
    created: list[TrackingConnection] = []

    def tracking_connect(*args, **kwargs):
        kwargs["factory"] = TrackingConnection
        conn = original_connect(*args, **kwargs)
        created.append(conn)
        return conn

    db_path = tmp_path / "lore.db"
    db = Database(str(db_path))
    dr = DRService(db=db, db_path=str(db_path), snapshot_dir=str(tmp_path / "snapshots"))
    db.insert_event(
        Event(
            id="event:test:dr-close-source",
            type="note",
            payload={"text": "before"},
            domains=["general"],
        )
    )
    snapshot = dr.create_snapshot(label="restore-close-source")

    monkeypatch.setattr("lore.disaster_recovery.sqlite3", SimpleNamespace(connect=tracking_connect))

    restored = dr.restore_snapshot(snapshot["snapshot_id"])

    assert restored["ok"] is True
    assert len(created) == 1
    assert created[0].closed is True


def test_snapshot_operations_are_blocked_in_multi_tenant_mode(tmp_path, monkeypatch):
    monkeypatch.setenv("LORE_ENABLE_MULTI_TENANT", "1")
    db_path = tmp_path / "lore.db"
    db = Database(str(db_path))
    dr = DRService(db=db, db_path=str(db_path), snapshot_dir=str(tmp_path / "snapshots"))

    with pytest.raises(RuntimeError, match="single_tenant_mode_required"):
        dr.create_snapshot(label="blocked", tenant_id="tenant-a")


def test_verify_snapshot_remains_available_in_multi_tenant_mode(tmp_path, monkeypatch):
    db_path = tmp_path / "lore.db"
    db = Database(str(db_path))
    db.insert_event(
        Event(
            id="event:test:dr-verify-multi",
            type="note",
            payload={"text": "before snapshot"},
            domains=["general"],
        )
    )
    dr = DRService(db=db, db_path=str(db_path), snapshot_dir=str(tmp_path / "snapshots"))
    snapshot = dr.create_snapshot(label="verify-before-multi")

    monkeypatch.setenv("LORE_ENABLE_MULTI_TENANT", "1")

    verify = dr.verify_snapshot(snapshot["snapshot_id"])
    assert verify["ok"] is True


def test_snapshot_rejects_path_traversal_label(tmp_path):
    db_path = tmp_path / "lore.db"
    db = Database(str(db_path))
    dr = DRService(db=db, db_path=str(db_path), snapshot_dir=str(tmp_path / "snapshots"))

    with pytest.raises(RuntimeError, match="invalid_snapshot_label"):
        dr.create_snapshot(label="..\\..\\escape")


def test_snapshot_accepts_dotted_label(tmp_path, monkeypatch):
    monkeypatch.delenv("LORE_ENABLE_MULTI_TENANT", raising=False)
    db_path = tmp_path / "lore.db"
    db = Database(str(db_path))
    dr = DRService(db=db, db_path=str(db_path), snapshot_dir=str(tmp_path / "snapshots"))

    snapshot = dr.create_snapshot(label="v1.0")
    assert snapshot["ok"] is True
    assert "v1.0" in snapshot["snapshot_id"]

    snapshot2 = dr.create_snapshot(label="2026-03-24")
    assert snapshot2["ok"] is True
    assert "2026-03-24" in snapshot2["snapshot_id"]


@pytest.mark.parametrize("label", [".", ".."])
def test_snapshot_rejects_dot_only_labels(tmp_path, monkeypatch, label):
    monkeypatch.delenv("LORE_ENABLE_MULTI_TENANT", raising=False)
    db_path = tmp_path / "lore.db"
    db = Database(str(db_path))
    dr = DRService(db=db, db_path=str(db_path), snapshot_dir=str(tmp_path / "snapshots"))

    with pytest.raises(RuntimeError, match="invalid_snapshot_label"):
        dr.create_snapshot(label=label)


def test_snapshot_rejects_forward_slash_traversal_label(tmp_path, monkeypatch):
    monkeypatch.delenv("LORE_ENABLE_MULTI_TENANT", raising=False)
    db_path = tmp_path / "lore.db"
    db = Database(str(db_path))
    dr = DRService(db=db, db_path=str(db_path), snapshot_dir=str(tmp_path / "snapshots"))

    with pytest.raises(RuntimeError, match="invalid_snapshot_label"):
        dr.create_snapshot(label="../../escape")


def test_verify_snapshot_rejects_storage_uri_outside_snapshot_dir(tmp_path):
    db_path = tmp_path / "lore.db"
    db = Database(str(db_path))
    dr = DRService(db=db, db_path=str(db_path), snapshot_dir=str(tmp_path / "snapshots"))
    snapshot = dr.create_snapshot(label="traversal-check")

    db.conn.execute(
        "UPDATE dr_snapshots SET storage_uri = ? WHERE id = ?",
        ("../../outside.db", snapshot["snapshot_id"]),
    )
    db.conn.commit()

    result = dr.verify_snapshot(snapshot["snapshot_id"])

    assert result["ok"] is False
    assert result["error"] == "invalid_storage_path"


def test_restore_snapshot_rejects_storage_uri_outside_snapshot_dir(tmp_path):
    db_path = tmp_path / "lore.db"
    db = Database(str(db_path))
    dr = DRService(db=db, db_path=str(db_path), snapshot_dir=str(tmp_path / "snapshots"))
    snapshot = dr.create_snapshot(label="restore-traversal")

    db.conn.execute(
        "UPDATE dr_snapshots SET storage_uri = ? WHERE id = ?",
        ("../../outside.db", snapshot["snapshot_id"]),
    )
    db.conn.commit()

    result = dr.restore_snapshot(snapshot["snapshot_id"])

    assert result["ok"] is False
    assert result["error"] == "invalid_storage_path"


def test_restore_snapshot_uses_database_transaction(tmp_path, monkeypatch):
    db_path = tmp_path / "lore.db"
    db = Database(str(db_path))
    dr = DRService(db=db, db_path=str(db_path), snapshot_dir=str(tmp_path / "snapshots"))

    db.insert_event(
        Event(
            id="event:test:dr-transaction-before",
            type="note",
            payload={"text": "before"},
            domains=["general"],
        )
    )
    snapshot = dr.create_snapshot(label="transaction")

    entered = {"count": 0}
    original_transaction = db.transaction

    def _wrapped_transaction():
        entered["count"] += 1
        return original_transaction()

    monkeypatch.setattr(db, "transaction", _wrapped_transaction)

    restored = dr.restore_snapshot(snapshot["snapshot_id"])

    assert restored["ok"] is True
    assert entered["count"] == 1
