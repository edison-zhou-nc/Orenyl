"""Embedding-oriented persistence methods for Database."""

from __future__ import annotations

import json

from ..embeddings import decode_vector, encode_vector
from ._base import BaseMixin


class EmbeddingMixin(BaseMixin):
    def upsert_event_embedding(
        self,
        event_id: str,
        vector: list[float],
        model_id: str,
        tenant_id: str = "default",
    ) -> None:
        self.conn.execute(
            """INSERT INTO event_embeddings (event_id, tenant_id, model_id, vector)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(event_id) DO UPDATE SET
                 tenant_id = excluded.tenant_id,
                 model_id = excluded.model_id,
                 vector = excluded.vector,
                 created_at = (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))""",
            (event_id, tenant_id or "default", model_id, encode_vector(vector)),
        )
        self._maybe_commit()

    def get_event_embedding(self, event_id: str, tenant_id: str = "") -> dict | None:
        row = self.conn.execute(
            """SELECT event_id, tenant_id, model_id, vector, created_at
               FROM event_embeddings
               WHERE event_id = ?
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (event_id, tenant_id, tenant_id),
        ).fetchone()
        if row is None:
            return None
        data = dict(row)
        data["vector"] = decode_vector(data["vector"])
        return data

    def upsert_fact_embedding(
        self,
        fact_id: str,
        vector: list[float],
        model_id: str,
        tenant_id: str = "default",
    ) -> None:
        self.conn.execute(
            """INSERT INTO fact_embeddings (fact_id, tenant_id, model_id, vector)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(fact_id) DO UPDATE SET
                 tenant_id = excluded.tenant_id,
                 model_id = excluded.model_id,
                 vector = excluded.vector,
                 created_at = (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))""",
            (fact_id, tenant_id or "default", model_id, encode_vector(vector)),
        )
        self._maybe_commit()

    def get_fact_embeddings(self, fact_ids: list[str], tenant_id: str = "") -> dict[str, dict]:
        if not fact_ids:
            return {}
        fact_ids_json = json.dumps(fact_ids)
        rows = self.conn.execute(
            """SELECT fact_id, tenant_id, model_id, vector, created_at
               FROM fact_embeddings
               WHERE fact_id IN (SELECT value FROM json_each(?))
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (fact_ids_json, tenant_id, tenant_id),
        ).fetchall()
        result: dict[str, dict] = {}
        for row in rows:
            data = dict(row)
            data["vector"] = decode_vector(data["vector"])
            result[data["fact_id"]] = data
        return result
