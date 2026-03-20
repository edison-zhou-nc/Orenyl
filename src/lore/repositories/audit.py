"""Audit-oriented persistence methods for Database."""

from __future__ import annotations

import json

from ._base import BaseMixin


class AuditMixin(BaseMixin):
    def log_retrieval(
        self,
        query: str,
        context_pack: str,
        trace: str,
        tenant_id: str = "default",
    ):
        self.conn.execute(
            (
                "INSERT INTO retrieval_logs "
                "(tenant_id, query, context_pack, trace) VALUES (?, ?, ?, ?)"
            ),
            (tenant_id or "default", query, context_pack, trace),
        )
        self._maybe_commit()

    def get_retrieval_logs(self, limit: int = 20, tenant_id: str = "") -> list[dict]:
        rows = self.conn.execute(
            """SELECT * FROM retrieval_logs
               WHERE (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)
               ORDER BY ts DESC
               LIMIT ?""",
            (tenant_id, tenant_id, limit),
        ).fetchall()
        result = []
        for row in rows:
            data = dict(row)
            data["context_pack"] = json.loads(data["context_pack"])
            data["trace"] = json.loads(data["trace"])
            result.append(data)
        return result

    def delete_retrieval_logs(self, tenant_id: str = "") -> int:
        cur = self.conn.execute(
            """DELETE FROM retrieval_logs
               WHERE (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (tenant_id, tenant_id),
        )
        self._maybe_commit()
        return cur.rowcount
