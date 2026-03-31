"""Lineage-oriented persistence methods for Database."""

from __future__ import annotations

import json

from ..models import Edge
from ._base import BaseMixin


class LineageMixin(BaseMixin):
    def insert_edge(self, edge: Edge):
        self.conn.execute(
            """INSERT OR IGNORE INTO edges (
                   tenant_id, parent_id, parent_type, child_id, child_type, relation
               )
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                edge.tenant_id,
                edge.parent_id,
                edge.parent_type,
                edge.child_id,
                edge.child_type,
                edge.relation,
            ),
        )
        self._maybe_commit()

    def get_children(self, parent_id: str, tenant_id: str = "") -> list[dict]:
        rows = self.conn.execute(
            """SELECT * FROM edges
               WHERE parent_id = ?
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (parent_id, tenant_id, tenant_id),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_parents(self, child_id: str, tenant_id: str = "") -> list[dict]:
        rows = self.conn.execute(
            """SELECT * FROM edges
               WHERE child_id = ?
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (child_id, tenant_id, tenant_id),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_parents_for_children(
        self,
        child_ids: list[str],
        tenant_id: str = "",
    ) -> dict[str, list[dict]]:
        if not child_ids:
            return {}
        child_ids_json = json.dumps(child_ids)
        rows = self.conn.execute(
            """SELECT * FROM edges
               WHERE child_id IN (SELECT value FROM json_each(?))
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (child_ids_json, tenant_id, tenant_id),
        ).fetchall()
        grouped: dict[str, list[dict]] = {child_id: [] for child_id in child_ids}
        for row in rows:
            edge = dict(row)
            grouped.setdefault(edge["child_id"], []).append(edge)
        return grouped

    def get_downstream_facts(self, item_id: str, tenant_id: str = "") -> list[str]:
        """Recursively find downstream facts using a single SQL CTE."""
        rows = self.conn.execute(
            """
            WITH RECURSIVE graph(child_id, depth) AS (
                SELECT child_id, 1 FROM edges
                WHERE parent_id = ?
                  AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)
                UNION ALL
                SELECT e.child_id, g.depth + 1
                FROM edges e
                JOIN graph g ON e.parent_id = g.child_id
                WHERE g.depth < 100
                  AND (NULLIF(?, '') IS NULL OR COALESCE(e.tenant_id, 'default') = ?)
            )
            SELECT DISTINCT child_id FROM graph ORDER BY child_id
            """,
            (item_id, tenant_id, tenant_id, tenant_id, tenant_id),
        ).fetchall()
        return [str(row["child_id"]) for row in rows]

    def delete_edges_for_item(self, item_id: str, tenant_id: str = "") -> int:
        cur = self.conn.execute(
            """DELETE FROM edges
               WHERE (parent_id = ? OR child_id = ?)
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (item_id, item_id, tenant_id, tenant_id),
        )
        self._maybe_commit()
        return cur.rowcount

    def hard_delete_facts_by_source(self, event_id: str, tenant_id: str = "") -> int:
        rows = self.conn.execute(
            """SELECT child_id
               FROM edges
               WHERE parent_id = ?
                 AND parent_type = 'event'
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (event_id, tenant_id, tenant_id),
        ).fetchall()
        fact_ids = [row[0] for row in rows]
        deleted = 0
        for fact_id in fact_ids:
            self.delete_edges_for_item(fact_id, tenant_id=tenant_id)
            cur = self.conn.execute(
                """DELETE FROM facts
                   WHERE id = ?
                     AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
                (fact_id, tenant_id, tenant_id),
            )
            deleted += cur.rowcount
        self._maybe_commit()
        return deleted

    def run_vacuum(self) -> None:
        # SQLite rejects VACUUM inside a transaction, so callers must invoke this
        # outside Database.transaction().
        self.conn.execute("VACUUM")
