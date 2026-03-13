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
