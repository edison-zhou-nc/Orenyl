"""Consent ledger helpers."""

from __future__ import annotations

from .db import Database
from .models import ConsentRecord


class ConsentService:
    def __init__(self, db: Database):
        self.db = db

    def record(
        self,
        tenant_id: str,
        subject_id: str,
        purpose: str,
        status: str,
        legal_basis: str = "",
        source: str = "user",
        metadata: dict | None = None,
    ) -> int:
        return self.db.insert_consent_record(
            ConsentRecord(
                tenant_id=tenant_id or "default",
                subject_id=subject_id,
                purpose=purpose,
                status=status,
                legal_basis=legal_basis,
                source=source,
                metadata=metadata or {},
            )
        )

    def is_processing_allowed(self, subject_id: str, purpose: str, tenant_id: str = "") -> bool:
        """Return whether processing is allowed for a subject-purpose pair.

        Current policy defaults to allow when no consent record exists. This supports
        legitimate-interest/contractual bases in deployments that do not require
        explicit opt-in for every purpose.
        """
        status = self.db.latest_consent_status(
            subject_id=subject_id,
            purpose=purpose,
            tenant_id=tenant_id,
        )
        if status is None:
            return True
        return status.lower() in {"granted", "allow", "allowed"}
