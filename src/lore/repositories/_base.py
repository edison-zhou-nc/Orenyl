"""Shared helpers for Database mixins."""

import sqlite3

from ..config import multi_tenant_enabled


class BaseMixin:
    conn: sqlite3.Connection
    _in_transaction: bool

    def _maybe_commit(self):
        """Commit unless the repository is inside an explicit transaction."""
        if not getattr(self, "_in_transaction", False):
            self.conn.commit()

    def _require_tenant_scope(self, tenant_id: str = "") -> str:
        normalized = str(tenant_id or "").strip()
        if multi_tenant_enabled() and not normalized:
            raise PermissionError("tenant_scope_required")
        return normalized
