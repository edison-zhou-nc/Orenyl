from __future__ import annotations

from lore.article30 import generate_article30_report
from lore.db import Database
from lore.models import ConsentRecord, Event


def test_generate_article30_report_contains_required_sections():
    db = Database(":memory:")
    db.insert_event(
        Event(
            id="event:test:a30-1",
            type="med_started",
            payload={"name": "metformin"},
            domains=["health"],
            metadata={"subject_id": "user:123"},
        )
    )
    db.insert_event(
        Event(
            id="event:test:a30-2",
            type="role_assigned",
            payload={"role": "lead"},
            domains=["career"],
            metadata={"subject_id": "user:123"},
        )
    )
    db.insert_consent_record(
        ConsentRecord(
            tenant_id="default",
            subject_id="user:123",
            purpose="retrieval",
            status="granted",
            legal_basis="consent",
        )
    )

    report = generate_article30_report(db)

    assert report["controller"]
    assert report["purposes"]
    assert report["retention_policies"] is not None
    assert report["recipients"] is not None
