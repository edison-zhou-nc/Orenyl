from lore.federation import SyncEnvelope, sign_envelope, validate_envelope


def test_sync_envelope_rejects_invalid_signature():
    envelope = SyncEnvelope(
        envelope_id="env-1",
        tenant_id="tenant-a",
        node_id="node-a",
        idempotency_key="idem-1",
        vector_clock={"node-a": 1},
        payload={"op": "upsert", "item_id": "fact:1"},
    )
    envelope.signature = sign_envelope(envelope, key="k")
    envelope.payload["item_id"] = "fact:tampered"

    assert validate_envelope(envelope, key="k") is False
