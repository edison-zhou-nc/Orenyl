from __future__ import annotations

from orenyl.compliance import ComplianceService
from orenyl.db import Database
from orenyl.lineage import LineageEngine
from orenyl.models import Event


def test_subject_portability_export_returns_manifest_and_subject_scoped_records():
    db = Database(":memory:")
    engine = LineageEngine(db)
    service = ComplianceService(db, engine)

    target = Event(
        id="event:test:subject-u123-export",
        type="med_started",
        payload={"name": "metformin"},
        metadata={"subject_id": "user:123"},
    )
    other = Event(
        id="event:test:subject-u999-export",
        type="med_started",
        payload={"name": "atorvastatin"},
        metadata={"subject_id": "user:999"},
    )
    db.insert_event(target)
    db.insert_event(other)
    engine.derive_facts_for_event(db.get_event(target.id))
    engine.derive_facts_for_event(db.get_event(other.id))

    payload = service.export_subject_data(subject_id="user:123")

    assert payload["ok"] is True
    assert payload["manifest"]["sha256"]
    assert payload["manifest"]["record_count"] > 0
    event_ids = {item["id"] for item in payload["records"] if item["kind"] == "event"}
    assert target.id in event_ids
    assert other.id not in event_ids
    request_row = db.conn.execute(
        "SELECT request_type, status FROM subject_requests WHERE subject_id = ?",
        ("user:123",),
    ).fetchone()
    assert request_row is not None
    assert request_row["request_type"] == "portability"
    assert request_row["status"] == "completed"
