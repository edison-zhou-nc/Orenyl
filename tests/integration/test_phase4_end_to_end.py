from __future__ import annotations

from lore.compliance import ComplianceService
from lore.consent import ConsentService
from lore.db import Database
from lore.disaster_recovery import DRService
from lore.lineage import LineageEngine
from lore.models import Event


def test_phase4_end_to_end_subject_lifecycle(tmp_path):
    db_path = tmp_path / "lore.db"
    db = Database(str(db_path))
    engine = LineageEngine(db)
    compliance = ComplianceService(db, engine)
    consent = ConsentService(db)
    dr = DRService(db=db, db_path=str(db_path), snapshot_dir=str(tmp_path / "snapshots"))

    consent.record(
        tenant_id="default",
        subject_id="user:123",
        purpose="retrieval",
        status="granted",
        legal_basis="consent",
    )
    db.insert_event(
        Event(
            id="event:test:e2e:u123",
            type="med_started",
            payload={"name": "metformin"},
            domains=["health"],
            metadata={"subject_id": "user:123"},
        )
    )
    export_before = compliance.export_subject_data(subject_id="user:123")
    assert export_before["ok"] is True
    assert export_before["manifest"]["record_count"] >= 1

    snapshot = dr.create_snapshot(label="phase4-e2e")
    assert snapshot["ok"] is True

    consent.record(
        tenant_id="default",
        subject_id="user:123",
        purpose="retrieval",
        status="withdrawn",
        legal_basis="withdrawal",
    )
    assert consent.is_processing_allowed("user:123", "retrieval") is False

    erased = compliance.erase_subject_data(subject_id="user:123", mode="hard")
    assert erased["ok"] is True
    assert erased["deleted_event_count"] >= 1
