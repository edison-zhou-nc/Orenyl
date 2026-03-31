"""Federation-oriented persistence methods for Database."""

from __future__ import annotations

import json
import sqlite3
from typing import Any, cast

from ._base import BaseMixin


class FederationMixin(BaseMixin):
    def append_sync_journal_entry(
        self,
        tenant_id: str,
        direction: str,
        envelope_id: str,
        idempotency_key: str,
        payload: dict[str, Any],
        status: str = "pending",
    ) -> bool:
        try:
            self.conn.execute(
                """INSERT INTO sync_journal (
                       tenant_id, direction, envelope_id, idempotency_key, payload, status
                   )
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    tenant_id,
                    direction,
                    envelope_id,
                    idempotency_key,
                    json.dumps(payload or {}),
                    status,
                ),
            )
        except sqlite3.IntegrityError:
            return False
        self._maybe_commit()
        return True

    def list_sync_journal_entries(
        self,
        tenant_id: str,
        direction: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        safe_limit = max(1, min(int(limit), 1000))
        rows = self.conn.execute(
            """SELECT *
               FROM sync_journal
               WHERE tenant_id = ?
                 AND (NULLIF(?, '') IS NULL OR direction = ?)
                 AND (NULLIF(?, '') IS NULL OR status = ?)
               ORDER BY id ASC
               LIMIT ?""",
            (
                tenant_id,
                direction or "",
                direction or "",
                status or "",
                status or "",
                safe_limit,
            ),
        ).fetchall()
        entries: list[dict] = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item.get("payload") or "{}")
            entries.append(item)
        return entries

    def update_sync_journal_status(
        self,
        tenant_id: str,
        direction: str,
        idempotency_key: str,
        status: str,
    ) -> bool:
        cur = self.conn.execute(
            """UPDATE sync_journal
               SET status = ?
               WHERE tenant_id = ?
                 AND direction = ?
                 AND idempotency_key = ?""",
            (status, tenant_id, direction, idempotency_key),
        )
        self._maybe_commit()
        return cur.rowcount > 0

    def sync_journal_count(self, tenant_id: str = "") -> int:
        row = self.conn.execute(
            """SELECT COUNT(*) AS c
               FROM sync_journal
               WHERE (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (tenant_id, tenant_id),
        ).fetchone()
        return int(row["c"]) if row is not None else 0

    def get_latest_applied_journal_entry_by_item(
        self,
        tenant_id: str,
        item_id: str,
        direction: str = "inbound",
    ) -> dict[str, Any] | None:
        row = self.conn.execute(
            """SELECT payload
               FROM sync_journal
               WHERE tenant_id = ?
                 AND direction = ?
                 AND status = 'applied'
                 AND json_extract(payload, '$.item_id') = ?
               ORDER BY id DESC
               LIMIT 1""",
            (tenant_id, direction, item_id),
        ).fetchone()
        if row is None:
            return None
        return cast(dict[str, Any], json.loads(str(row["payload"] or "{}")))
