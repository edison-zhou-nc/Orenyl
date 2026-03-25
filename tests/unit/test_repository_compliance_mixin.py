from lore.db import Database
from lore.models import ConsentRecord, DRSnapshot, SubjectRequest, Tombstone


def test_compliance_repository_round_trips_tombstones_consent_and_snapshots():
    db = Database(":memory:")

    db.insert_tombstone(
        Tombstone(
            target_id="event:test:repo-c1",
            target_type="event",
            cascade_invalidated=["fact:test:repo-c1"],
        )
    )
    tombstone = db.get_tombstones(target_id="event:test:repo-c1")[0]
    assert tombstone["cascade_invalidated"] == ["fact:test:repo-c1"]

    db.insert_consent_record(
        ConsentRecord(
            tenant_id="default",
            subject_id="user:consent",
            purpose="retrieval",
            status="withdrawn",
        )
    )
    db.insert_consent_record(
        ConsentRecord(
            tenant_id="default",
            subject_id="user:denied",
            purpose="retrieval",
            status="denied",
        )
    )
    assert db.latest_consent_status("user:consent", "retrieval") == "withdrawn"
    # withdrawn_subject_ids excludes any status not in {granted, allow, allowed},
    # not just 'withdrawn' — mirrors ConsentService.is_processing_allowed semantics.
    assert db.withdrawn_subject_ids(
        ["user:consent", "user:denied", "user:other"], "retrieval"
    ) == {"user:consent", "user:denied"}

    request = SubjectRequest(
        request_id="req:test:repo-c1",
        tenant_id="default",
        subject_id="user:consent",
        request_type="export",
    )
    assert db.create_subject_request(request) == request.request_id

    snapshot = DRSnapshot(
        snapshot_id="snapshot:test:repo-c1",
        tenant_id="default",
        metadata={"kind": "manual"},
    )
    assert db.insert_dr_snapshot(snapshot) == snapshot.snapshot_id
    assert db.get_dr_snapshot(snapshot.snapshot_id)["metadata"] == {"kind": "manual"}
