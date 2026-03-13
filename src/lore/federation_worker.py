"""Federation worker primitives for inbound idempotent apply."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .db import Database
from .federation import SyncEnvelope, incoming_wins_lww


@dataclass(frozen=True)
class ApplyResult:
    applied: bool
    reason: str = ""


class FederationWorker:
    def __init__(self, db: Database, node_id: str):
        self.db = db
        self.node_id = node_id

    def apply_inbound(self, envelope: SyncEnvelope) -> ApplyResult:
        if not envelope.tenant_id or not envelope.idempotency_key:
            return ApplyResult(applied=False, reason="invalid_envelope")

        journal_payload = self._journal_payload(envelope)
        inserted = self.db.append_sync_journal_entry(
            tenant_id=envelope.tenant_id,
            direction="inbound",
            envelope_id=envelope.envelope_id,
            idempotency_key=envelope.idempotency_key,
            payload=journal_payload,
            status="pending",
        )
        if not inserted:
            return ApplyResult(applied=False, reason="replay_ignored")

        if not self._wins_conflict_check(envelope):
            self.db.update_sync_journal_status(
                tenant_id=envelope.tenant_id,
                direction="inbound",
                idempotency_key=envelope.idempotency_key,
                status="conflict_ignored",
            )
            return ApplyResult(applied=False, reason="lww_conflict_lost")

        self.db.update_sync_journal_status(
            tenant_id=envelope.tenant_id,
            direction="inbound",
            idempotency_key=envelope.idempotency_key,
            status="applied",
        )
        return ApplyResult(applied=True)

    def _wins_conflict_check(self, envelope: SyncEnvelope) -> bool:
        item_id = str((envelope.payload or {}).get("item_id", "")).strip()
        if not item_id:
            return True
        incoming_updated_at = str((envelope.payload or {}).get("updated_at", ""))
        latest = self._latest_applied_entry(envelope.tenant_id, item_id)
        if latest is None:
            return True
        current_updated_at = str(latest.get("updated_at", ""))
        current_node_id = str(latest.get("node_id", ""))
        return incoming_wins_lww(
            current_updated_at=current_updated_at,
            current_node_id=current_node_id,
            incoming_updated_at=incoming_updated_at,
            incoming_node_id=envelope.node_id,
        )

    def _latest_applied_entry(self, tenant_id: str, item_id: str) -> dict[str, Any] | None:
        # TODO: Replace this bounded scan with a targeted DB query/index on payload.item_id.
        # Current Phase 3 scope keeps this simple for SQLite-backed single-node operation.
        applied_rows = self.db.list_sync_journal_entries(
            tenant_id=tenant_id,
            direction="inbound",
            status="applied",
            limit=1000,
        )
        matching = [
            row["payload"]
            for row in applied_rows
            if isinstance(row.get("payload"), dict) and row["payload"].get("item_id") == item_id
        ]
        if not matching:
            return None
        matching.sort(
            key=lambda payload: (
                str(payload.get("updated_at", "")),
                str(payload.get("node_id", "")),
            ),
            reverse=True,
        )
        return matching[0]

    @staticmethod
    def _journal_payload(envelope: SyncEnvelope) -> dict[str, Any]:
        payload = dict(envelope.payload or {})
        payload.setdefault("updated_at", "")
        payload["node_id"] = envelope.node_id
        payload["item_id"] = str(payload.get("item_id", ""))
        return payload
