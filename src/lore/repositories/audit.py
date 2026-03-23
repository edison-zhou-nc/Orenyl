"""Audit-oriented persistence methods for Database."""

from __future__ import annotations

import json

from ._base import BaseMixin


class AuditMixin(BaseMixin):
    @staticmethod
    def _retrieval_log_references_lineage(
        context_pack_raw: str,
        trace_raw: str,
        referenced_ids: set[str],
    ) -> bool:
        try:
            context_pack = json.loads(context_pack_raw)
        except (TypeError, ValueError):
            context_pack = {}
        try:
            trace = json.loads(trace_raw)
        except (TypeError, ValueError):
            trace = []

        for item in context_pack.get("items", []):
            if str(item.get("id", "")) in referenced_ids:
                return True
            provenance = item.get("provenance") or {}
            derived_from = {str(item_id) for item_id in provenance.get("derived_from", [])}
            if derived_from & referenced_ids:
                return True

        for entry in trace:
            if str(entry.get("item_id", "")) in referenced_ids:
                return True
            lineage = {str(item_id) for item_id in entry.get("lineage", [])}
            if lineage & referenced_ids:
                return True

        return False

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

    def delete_retrieval_logs_for_lineage(
        self,
        referenced_ids: list[str],
        tenant_id: str = "",
    ) -> int:
        references = {str(item_id) for item_id in referenced_ids if str(item_id).strip()}
        if not references:
            return 0

        rows = self.conn.execute(
            """SELECT id, context_pack, trace FROM retrieval_logs
               WHERE (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (tenant_id, tenant_id),
        ).fetchall()
        delete_ids = [
            int(row["id"])
            for row in rows
            if self._retrieval_log_references_lineage(
                str(row["context_pack"]),
                str(row["trace"]),
                references,
            )
        ]
        if not delete_ids:
            return 0

        delete_ids_json = json.dumps(delete_ids)
        cur = self.conn.execute(
            """DELETE FROM retrieval_logs
               WHERE id IN (SELECT value FROM json_each(?))""",
            (delete_ids_json,),
        )
        self._maybe_commit()
        return cur.rowcount
