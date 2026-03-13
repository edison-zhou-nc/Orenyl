from lore.db import Database


def test_sync_journal_append_read_update_status():
    db = Database(":memory:")

    inserted = db.append_sync_journal_entry(
        tenant_id="tenant-a",
        direction="outbound",
        envelope_id="env-1",
        idempotency_key="idem-1",
        payload={"op": "upsert", "item_id": "fact:1"},
    )
    assert inserted is True

    rows = db.list_sync_journal_entries(
        tenant_id="tenant-a",
        direction="outbound",
        status="pending",
    )
    assert len(rows) == 1
    assert rows[0]["envelope_id"] == "env-1"
    assert rows[0]["payload"]["item_id"] == "fact:1"

    updated = db.update_sync_journal_status(
        tenant_id="tenant-a",
        direction="outbound",
        idempotency_key="idem-1",
        status="applied",
    )
    assert updated is True

    applied_rows = db.list_sync_journal_entries(
        tenant_id="tenant-a",
        direction="outbound",
        status="applied",
    )
    assert len(applied_rows) == 1
    assert applied_rows[0]["idempotency_key"] == "idem-1"


def test_sync_journal_idempotency_key_is_unique_per_tenant_and_direction():
    db = Database(":memory:")

    first = db.append_sync_journal_entry(
        tenant_id="tenant-a",
        direction="inbound",
        envelope_id="env-1",
        idempotency_key="idem-dup",
        payload={"op": "upsert"},
    )
    second = db.append_sync_journal_entry(
        tenant_id="tenant-a",
        direction="inbound",
        envelope_id="env-2",
        idempotency_key="idem-dup",
        payload={"op": "delete"},
    )

    assert first is True
    assert second is False
