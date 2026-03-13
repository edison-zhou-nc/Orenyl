"""Federation sync envelope primitives."""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass, field
from typing import Any

from .models import now_iso


@dataclass
class SyncEnvelope:
    envelope_id: str
    tenant_id: str
    node_id: str
    idempotency_key: str
    vector_clock: dict[str, int]
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    signature: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = now_iso()


def sign_envelope(envelope: SyncEnvelope, key: str) -> str:
    message = _canonical_message(envelope)
    return hmac.new(key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()


def validate_envelope(envelope: SyncEnvelope, key: str) -> bool:
    if not envelope.tenant_id or not envelope.node_id or not envelope.idempotency_key:
        return False
    if not isinstance(envelope.vector_clock, dict):
        return False
    expected = sign_envelope(envelope, key=key)
    provided = str(envelope.signature or "")
    return hmac.compare_digest(provided, expected)


def incoming_wins_lww(
    current_updated_at: str,
    current_node_id: str,
    incoming_updated_at: str,
    incoming_node_id: str,
) -> bool:
    """LWW compare: updated_at first, then node_id lexical tie-break."""
    if incoming_updated_at != current_updated_at:
        return incoming_updated_at > current_updated_at
    return incoming_node_id > current_node_id


def _canonical_message(envelope: SyncEnvelope) -> str:
    payload = {
        "envelope_id": envelope.envelope_id,
        "tenant_id": envelope.tenant_id,
        "node_id": envelope.node_id,
        "idempotency_key": envelope.idempotency_key,
        "vector_clock": envelope.vector_clock,
        "payload": envelope.payload,
        "created_at": envelope.created_at,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))
