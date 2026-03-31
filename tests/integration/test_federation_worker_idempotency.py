from lore.db import Database
from lore.federation import SyncEnvelope
from lore.federation_worker import FederationWorker


def test_replayed_envelope_is_ignored_once_applied():
    db = Database(":memory:")
    worker = FederationWorker(db=db, node_id="node-local")
    envelope = SyncEnvelope(
        envelope_id="env-1",
        tenant_id="tenant-a",
        node_id="node-remote",
        idempotency_key="idem-1",
        vector_clock={"node-remote": 1},
        payload={"item_id": "fact:1", "updated_at": "2026-03-13T00:00:00Z"},
    )

    first = worker.apply_inbound(envelope)
    second = worker.apply_inbound(envelope)

    assert first.applied is True
    assert second.applied is False


def test_latest_applied_entry_finds_entries_beyond_repository_limit():
    db = Database(":memory:")
    worker = FederationWorker(db=db, node_id="node-local")

    for idx in range(1001):
        item_id = f"item-{idx}" if idx < 1000 else "target-item"
        db.append_sync_journal_entry(
            tenant_id="tenant-a",
            direction="inbound",
            envelope_id=f"env-{idx}",
            idempotency_key=f"idem-{idx}",
            payload={
                "item_id": item_id,
                "updated_at": f"2026-03-13T00:00:{idx % 60:02d}Z",
                "node_id": "node-remote",
            },
            status="applied",
        )

    latest = worker._latest_applied_entry("tenant-a", "target-item")

    assert latest is not None
    assert latest["item_id"] == "target-item"
