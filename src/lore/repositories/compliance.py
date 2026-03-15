"""Compliance-oriented persistence methods for Database."""

from __future__ import annotations

import json

from ..models import ConsentRecord, DRSnapshot, SubjectRequest, Tombstone
from ._base import BaseMixin


class ComplianceMixin(BaseMixin):
    def insert_tombstone(self, tombstone: Tombstone):
        self.conn.execute(
            """INSERT INTO tombstones (
                   tenant_id, target_id, target_type, reason, deleted_at, cascade_invalidated
               )
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                tombstone.tenant_id,
                tombstone.target_id,
                tombstone.target_type,
                tombstone.reason,
                tombstone.deleted_at,
                json.dumps(tombstone.cascade_invalidated),
            ),
        )
        self._maybe_commit()

    def get_tombstones(self, target_id: str | None = None, tenant_id: str = "") -> list[dict]:
        if target_id:
            rows = self.conn.execute(
                """SELECT * FROM tombstones
                   WHERE target_id = ?
                     AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
                (target_id, tenant_id, tenant_id),
            ).fetchall()
        else:
            rows = self.conn.execute(
                """SELECT * FROM tombstones
                   WHERE (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
                (tenant_id, tenant_id),
            ).fetchall()
        result = []
        for row in rows:
            data = dict(row)
            data["cascade_invalidated"] = json.loads(data["cascade_invalidated"])
            result.append(data)
        return result

    def insert_consent_record(self, record: ConsentRecord) -> int:
        cursor = self.conn.execute(
            """INSERT INTO consent_records (
                   tenant_id, subject_id, purpose, status,
                   legal_basis, source, effective_at, metadata
               )
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record.tenant_id or "default",
                record.subject_id,
                record.purpose,
                record.status,
                record.legal_basis,
                record.source,
                record.effective_at,
                json.dumps(record.metadata),
            ),
        )
        self._maybe_commit()
        return int(cursor.lastrowid)

    def latest_consent_status(
        self,
        subject_id: str,
        purpose: str,
        tenant_id: str = "",
    ) -> str | None:
        row = self.conn.execute(
            """SELECT status
               FROM consent_records
               WHERE subject_id = ?
                 AND purpose = ?
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)
               ORDER BY effective_at DESC, recorded_at DESC, id DESC
               LIMIT 1""",
            (subject_id, purpose, tenant_id, tenant_id),
        ).fetchone()
        if row is None:
            return None
        return str(row["status"])

    def withdrawn_subject_ids(
        self,
        subject_ids: list[str],
        purpose: str,
        tenant_id: str = "",
    ) -> set[str]:
        normalized = sorted({subject_id for subject_id in subject_ids if subject_id})
        if not normalized:
            return set()
        subject_ids_json = json.dumps(normalized)
        rows = self.conn.execute(
            """SELECT x.subject_id, (
                   SELECT cr.status
                   FROM consent_records cr
                   WHERE cr.subject_id = x.subject_id
                     AND cr.purpose = ?
                     AND (NULLIF(?, '') IS NULL OR COALESCE(cr.tenant_id, 'default') = ?)
                   ORDER BY cr.effective_at DESC, cr.recorded_at DESC, cr.id DESC
                   LIMIT 1
               ) AS latest_status
               FROM (SELECT value AS subject_id FROM json_each(?)) x""",
            (purpose, tenant_id, tenant_id, subject_ids_json),
        ).fetchall()
        return {
            str(row["subject_id"])
            for row in rows
            if str(row["latest_status"] or "").lower() == "withdrawn"
        }

    def list_consent_purposes(self, tenant_id: str = "") -> list[dict[str, str]]:
        rows = self.conn.execute(
            """SELECT DISTINCT purpose, legal_basis
               FROM consent_records
               WHERE (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)
               ORDER BY purpose ASC""",
            (tenant_id, tenant_id),
        ).fetchall()
        return [
            {
                "purpose": str(row["purpose"] or ""),
                "legal_basis": str(row["legal_basis"] or ""),
            }
            for row in rows
        ]

    def create_subject_request(self, request: SubjectRequest) -> str:
        self.conn.execute(
            """INSERT INTO subject_requests (
                   id, tenant_id, subject_id, request_type, status, opened_at, closed_at, details
               )
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                request.request_id,
                request.tenant_id or "default",
                request.subject_id,
                request.request_type,
                request.status,
                request.opened_at,
                request.closed_at,
                json.dumps(request.details),
            ),
        )
        self._maybe_commit()
        return request.request_id

    def has_agent_permission(
        self,
        tenant_id: str,
        agent_id: str,
        domain: str,
        action: str,
        at_ts: str,
    ) -> bool:
        row = self.conn.execute(
            """SELECT 1
               FROM agent_permissions
               WHERE tenant_id = ?
                 AND agent_id = ?
                 AND action = ?
                 AND effect = 'allow'
                 AND (domain = ? OR domain = '*')
                 AND (expires_at IS NULL OR expires_at > ?)
               LIMIT 1""",
            (tenant_id, agent_id, action, domain, at_ts),
        ).fetchone()
        return row is not None

    def has_delegation_grant(
        self,
        tenant_id: str,
        grantee_agent_id: str,
        domain: str,
        action: str,
        at_ts: str,
    ) -> bool:
        row = self.conn.execute(
            """SELECT 1
               FROM delegation_grants
               WHERE tenant_id = ?
                 AND grantee_agent_id = ?
                 AND action = ?
                 AND (domain = ? OR domain = '*')
                 AND (fact_id IS NULL OR fact_id = '')
                 AND expires_at > ?
               LIMIT 1""",
            (tenant_id, grantee_agent_id, action, domain, at_ts),
        ).fetchone()
        return row is not None

    def insert_dr_snapshot(self, snapshot: DRSnapshot) -> str:
        self.conn.execute(
            """INSERT INTO dr_snapshots (
                   id, tenant_id, wal_lsn, checksum, storage_uri, created_at, verified_at, metadata
               )
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                snapshot.snapshot_id,
                snapshot.tenant_id or "default",
                snapshot.wal_lsn,
                snapshot.checksum,
                snapshot.storage_uri,
                snapshot.created_at,
                snapshot.verified_at,
                json.dumps(snapshot.metadata),
            ),
        )
        self._maybe_commit()
        return snapshot.snapshot_id

    def get_dr_snapshot(self, snapshot_id: str, tenant_id: str = "") -> dict | None:
        row = self.conn.execute(
            """SELECT *
               FROM dr_snapshots
               WHERE id = ?
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (snapshot_id, tenant_id, tenant_id),
        ).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["metadata"] = json.loads(result.get("metadata", "{}"))
        return result
