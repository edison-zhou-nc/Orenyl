"""Audit-oriented persistence methods for Database."""

from __future__ import annotations

import json

from ._base import BaseMixin


class AuditMixin(BaseMixin):
    def log_retrieval(self, query: str, context_pack: str, trace: str):
        self.conn.execute(
            "INSERT INTO retrieval_logs (query, context_pack, trace) VALUES (?, ?, ?)",
            (query, context_pack, trace),
        )
        self._maybe_commit()

    def get_retrieval_logs(self, limit: int = 20) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM retrieval_logs ORDER BY ts DESC LIMIT ?",
            (limit,),
        ).fetchall()
        result = []
        for row in rows:
            data = dict(row)
            data["context_pack"] = json.loads(data["context_pack"])
            data["trace"] = json.loads(data["trace"])
            result.append(data)
        return result
