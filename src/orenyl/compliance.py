"""Compliance workflows for subject rights automation."""

from __future__ import annotations

import hashlib
import json

from .db import Database
from .lineage import LineageEngine
from .models import SubjectRequest, new_id, now_iso


class ComplianceService:
    def __init__(self, db: Database, engine: LineageEngine):
        self.db = db
        self.engine = engine

    def erase_subject_data(
        self,
        subject_id: str,
        mode: str = "hard",
        tenant_id: str = "",
        reason: str = "subject_erasure",
    ) -> dict:
        normalized_tenant_id = tenant_id or "default"
        request_id = new_id("subject_request", "erasure")
        opened_at = now_iso()
        events = self.db.get_active_events_by_subject(subject_id=subject_id, tenant_id=tenant_id)
        if not events:
            result = {
                "ok": False,
                "error": "subject_not_found",
                "subject_id": subject_id,
                "mode": mode,
                "deleted_event_ids": [],
                "deleted_event_count": 0,
                "deletion_verified": True,
                "proofs": [],
            }
            with self.db.transaction():
                self._delete_subject_records(subject_id=subject_id, tenant_id=normalized_tenant_id)
                self.db.create_subject_request(
                    SubjectRequest(
                        request_id=request_id,
                        tenant_id=normalized_tenant_id,
                        subject_id=subject_id,
                        request_type="erasure",
                        status="completed",
                        opened_at=opened_at,
                        closed_at=now_iso(),
                        details=result,
                    )
                )
            return result
        deleted_event_ids: list[str] = []
        deletion_verified = True
        proofs: list[dict] = []
        for event in events:
            proof = self.engine.delete_and_recompute(
                target_id=event["id"],
                target_type="event",
                reason=reason,
                mode=mode,
                tenant_id=tenant_id,
            )
            proof_dict = proof.to_dict()
            proofs.append(proof_dict)
            deleted_event_ids.append(event["id"])
            deletion_verified = deletion_verified and bool(
                proof_dict.get("checks", {}).get("deletion_verified", False)
            )

        result = {
            "ok": True,
            "subject_id": subject_id,
            "mode": mode,
            "deleted_event_ids": deleted_event_ids,
            "deleted_event_count": len(deleted_event_ids),
            "deletion_verified": deletion_verified,
            "proofs": proofs,
        }
        with self.db.transaction():
            self._delete_subject_records(subject_id=subject_id, tenant_id=normalized_tenant_id)
            self.db.create_subject_request(
                SubjectRequest(
                    request_id=request_id,
                    tenant_id=normalized_tenant_id,
                    subject_id=subject_id,
                    request_type="erasure",
                    status="completed",
                    opened_at=opened_at,
                    closed_at=now_iso(),
                    details=result,
                )
            )
        return result

    def _delete_subject_records(self, subject_id: str, tenant_id: str) -> None:
        self.db.conn.execute(
            """DELETE FROM consent_records
               WHERE subject_id = ?
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (subject_id, tenant_id, tenant_id),
        )
        self.db.conn.execute(
            """DELETE FROM subject_requests
               WHERE subject_id = ?
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (subject_id, tenant_id, tenant_id),
        )

    def export_subject_data(self, subject_id: str, tenant_id: str = "") -> dict:
        request = SubjectRequest(
            request_id=new_id("subject_request", "portability"),
            tenant_id=tenant_id or "default",
            subject_id=subject_id,
            request_type="portability",
            status="completed",
            closed_at=now_iso(),
        )
        events = self.db.get_active_events_by_subject(subject_id=subject_id, tenant_id=tenant_id)
        fact_ids: set[str] = set()
        for event in events:
            fact_ids.update(self.db.get_downstream_facts(event["id"], tenant_id=tenant_id))
        facts = self.db.get_facts_by_ids(sorted(fact_ids), tenant_id=tenant_id)

        records: list[dict] = []
        for event in events:
            records.append(
                {
                    "id": event["id"],
                    "kind": "event",
                    "created_at": event.get("created_at", ""),
                    "data": event,
                }
            )
        for fact in facts:
            records.append(
                {
                    "id": fact["id"],
                    "kind": "fact",
                    "created_at": fact.get("created_at", ""),
                    "data": fact,
                }
            )
        records.sort(key=lambda item: (item.get("created_at", ""), item["id"]))

        per_record_hashes: list[str] = []
        for record in records:
            canonical = json.dumps(record, sort_keys=True, separators=(",", ":"))
            per_record_hashes.append(hashlib.sha256(canonical.encode("utf-8")).hexdigest())
        manifest_payload = "\n".join(per_record_hashes)
        manifest_sha = hashlib.sha256(manifest_payload.encode("utf-8")).hexdigest()

        result = {
            "ok": True,
            "subject_id": subject_id,
            "records": records,
            "manifest": {
                "record_count": len(records),
                "record_hashes": per_record_hashes,
                "sha256": manifest_sha,
            },
        }
        request.details = result
        self.db.create_subject_request(request)
        return result
