from lore.db import Database
from lore.federation import SyncEnvelope
from lore.federation_worker import FederationWorker


def test_lww_prefers_newer_updated_at_then_node_id():
    db = Database(":memory:")
    worker = FederationWorker(db=db, node_id="node-local")

    older = SyncEnvelope(
        envelope_id="env-old",
        tenant_id="tenant-a",
        node_id="node-a",
        idempotency_key="idem-old",
        vector_clock={"node-a": 1},
        payload={"item_id": "fact:1", "updated_at": "2026-03-13T00:00:00Z"},
    )
    newer = SyncEnvelope(
        envelope_id="env-new",
        tenant_id="tenant-a",
        node_id="node-b",
        idempotency_key="idem-new",
        vector_clock={"node-b": 1},
        payload={"item_id": "fact:1", "updated_at": "2026-03-13T00:00:01Z"},
    )
    tie_loser = SyncEnvelope(
        envelope_id="env-tie-loser",
        tenant_id="tenant-a",
        node_id="node-a",
        idempotency_key="idem-tie-loser",
        vector_clock={"node-a": 2},
        payload={"item_id": "fact:1", "updated_at": "2026-03-13T00:00:01Z"},
    )

    first = worker.apply_inbound(older)
    second = worker.apply_inbound(newer)
    third = worker.apply_inbound(tie_loser)

    assert first.applied is True
    assert second.applied is True
    assert third.applied is False
