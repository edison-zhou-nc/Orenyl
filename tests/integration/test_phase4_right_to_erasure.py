from __future__ import annotations

from orenyl.compliance import ComplianceService
from orenyl.db import Database
from orenyl.lineage import LineageEngine
from orenyl.models import Event


def test_right_to_erasure_deletes_subject_data_and_returns_proof():
    db = Database(":memory:")
    engine = LineageEngine(db)
    service = ComplianceService(db, engine)

    target = Event(
        id="event:test:subject-u123",
        type="med_started",
        payload={"name": "metformin"},
        metadata={"subject_id": "user:123"},
    )
    other = Event(
        id="event:test:subject-u999",
        type="med_started",
        payload={"name": "atorvastatin"},
        metadata={"subject_id": "user:999"},
    )
    db.insert_event(target)
    db.insert_event(other)

    result = service.erase_subject_data(subject_id="user:123", mode="hard")

    assert result["ok"] is True
    assert result["deleted_event_count"] == 1
    assert result["deletion_verified"] is True
    assert db.get_event(target.id) is None
    assert db.get_event(other.id) is not None
    request_row = db.conn.execute(
        "SELECT request_type, status FROM subject_requests WHERE subject_id = ?",
        ("user:123",),
    ).fetchone()
    assert request_row is not None
    assert request_row["request_type"] == "erasure"
    assert request_row["status"] == "completed"
