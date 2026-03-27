"""Fact-oriented persistence methods for Database."""

from __future__ import annotations

import json

from ..models import Fact
from ._base import BaseMixin


class FactMixin(BaseMixin):
    def _hydrate_fact_row(self, row) -> dict:
        data = dict(row)
        data["value"] = json.loads(data["value"])
        data["transform_config"] = json.loads(data["transform_config"])
        data["stale"] = bool(data["stale"])
        return data

    def insert_fact(self, fact: Fact) -> str:
        self.conn.execute(
            """INSERT INTO facts (
                   id, key, value, transform_config, stale, importance,
                   version, rule_id, rule_version, confidence, model_id,
                   tenant_id, valid_from, valid_to, created_at
               )
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                fact.id,
                fact.key,
                json.dumps(fact.value),
                json.dumps(fact.transform_config),
                int(fact.stale),
                fact.importance,
                fact.version,
                fact.rule_id,
                fact.rule_version,
                fact.confidence,
                fact.model_id,
                fact.tenant_id,
                fact.valid_from,
                fact.valid_to,
                fact.created_at,
            ),
        )
        self._maybe_commit()
        return fact.id

    def get_current_facts(self, key: str | None = None, tenant_id: str = "") -> list[dict]:
        """Get all valid, non-invalidated facts (optionally filtered by key)."""
        if key:
            rows = self.conn.execute(
                """SELECT * FROM facts
                   WHERE invalidated_at IS NULL
                     AND key = ?
                     AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)
                   ORDER BY version DESC""",
                (key, tenant_id, tenant_id),
            ).fetchall()
        else:
            rows = self.conn.execute(
                """SELECT * FROM facts
                   WHERE invalidated_at IS NULL
                     AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)
                   ORDER BY key, version DESC""",
                (tenant_id, tenant_id),
            ).fetchall()
        result = []
        seen_keys: set[str] = set()
        for row in rows:
            data = self._hydrate_fact_row(row)
            if data["key"] not in seen_keys:
                seen_keys.add(data["key"])
                result.append(data)
        return result

    def get_current_facts_by_domain(
        self,
        domain: str,
        tenant_id: str = "",
        agent_id: str = "",
        session_id: str = "",
    ) -> list[dict]:
        if domain and domain != "general":
            rows = self.conn.execute(
                """SELECT DISTINCT f.*
                   FROM facts f
                   WHERE f.invalidated_at IS NULL
                     AND (NULLIF(?, '') IS NULL OR COALESCE(f.tenant_id, 'default') = ?)
                     AND EXISTS (
                         SELECT 1
                         FROM edges e
                         JOIN event_domains ed ON ed.event_id = e.parent_id
                         JOIN events ev ON ev.id = e.parent_id
                         WHERE e.child_id = f.id
                           AND e.parent_type = 'event'
                           AND ed.domain = ?
                           AND ev.archived_at IS NULL
                           AND (NULLIF(?, '') IS NULL OR COALESCE(ev.tenant_id, 'default') = ?)
                     )
                     AND NOT EXISTS (
                         SELECT 1
                         FROM edges e2
                         JOIN events ev2 ON ev2.id = e2.parent_id
                         WHERE e2.child_id = f.id
                           AND e2.parent_type = 'event'
                           AND (NULLIF(?, '') IS NULL OR COALESCE(ev2.tenant_id, 'default') = ?)
                           AND (
                               (NULLIF(?, '') IS NOT NULL AND COALESCE(ev2.agent_id, '') <> ?)
                               OR (NULLIF(?, '') IS NOT NULL AND COALESCE(ev2.session_id, '') <> ?)
                           )
                     )
                   ORDER BY f.key, f.version DESC""",
                (
                    tenant_id,
                    tenant_id,
                    domain,
                    tenant_id,
                    tenant_id,
                    tenant_id,
                    tenant_id,
                    agent_id,
                    agent_id,
                    session_id,
                    session_id,
                ),
            ).fetchall()
        else:
            rows = self.conn.execute(
                """SELECT DISTINCT f.*
                   FROM facts f
                   WHERE f.invalidated_at IS NULL
                     AND (NULLIF(?, '') IS NULL OR COALESCE(f.tenant_id, 'default') = ?)
                     AND EXISTS (
                         SELECT 1
                         FROM edges e
                         JOIN events ev ON ev.id = e.parent_id
                         WHERE e.child_id = f.id
                           AND e.parent_type = 'event'
                           AND ev.archived_at IS NULL
                           AND (NULLIF(?, '') IS NULL OR COALESCE(ev.tenant_id, 'default') = ?)
                     )
                     AND NOT EXISTS (
                         SELECT 1
                         FROM edges e2
                         JOIN events ev2 ON ev2.id = e2.parent_id
                         WHERE e2.child_id = f.id
                           AND e2.parent_type = 'event'
                           AND (NULLIF(?, '') IS NULL OR COALESCE(ev2.tenant_id, 'default') = ?)
                           AND (
                               (NULLIF(?, '') IS NOT NULL AND COALESCE(ev2.agent_id, '') <> ?)
                               OR (NULLIF(?, '') IS NOT NULL AND COALESCE(ev2.session_id, '') <> ?)
                           )
                     )
                   ORDER BY f.key, f.version DESC""",
                (
                    tenant_id,
                    tenant_id,
                    tenant_id,
                    tenant_id,
                    tenant_id,
                    tenant_id,
                    agent_id,
                    agent_id,
                    session_id,
                    session_id,
                ),
            ).fetchall()
        result = []
        seen_keys: set[str] = set()
        for row in rows:
            data = self._hydrate_fact_row(row)
            if data["key"] not in seen_keys:
                seen_keys.add(data["key"])
                result.append(data)
        return result

    def get_restricted_fact_ids_for_export_domain(
        self,
        domain: str,
        tenant_id: str = "",
    ) -> list[str]:
        rows = self.conn.execute(
            """SELECT DISTINCT f.id
               FROM facts f
               WHERE f.invalidated_at IS NULL
                 AND (NULLIF(?, '') IS NULL OR COALESCE(f.tenant_id, 'default') = ?)
                 AND EXISTS (
                     SELECT 1
                     FROM edges e
                     LEFT JOIN event_domains ed
                       ON ed.event_id = e.parent_id
                      AND ed.domain = ?
                     JOIN events ev ON ev.id = e.parent_id
                     WHERE e.child_id = f.id
                       AND e.parent_type = 'event'
                       AND (
                           NULLIF(?, '') IS NULL
                           OR ? = 'general'
                           OR ed.domain IS NOT NULL
                       )
                       AND ev.archived_at IS NULL
                       AND (NULLIF(?, '') IS NULL OR COALESCE(ev.tenant_id, 'default') = ?)
                 )
                 AND EXISTS (
                     SELECT 1
                     FROM edges e2
                     JOIN events ev2 ON ev2.id = e2.parent_id
                     WHERE e2.child_id = f.id
                       AND e2.parent_type = 'event'
                       AND LOWER(COALESCE(ev2.sensitivity, '')) = 'restricted'
                       AND (NULLIF(?, '') IS NULL OR COALESCE(ev2.tenant_id, 'default') = ?)
                 )
               ORDER BY f.id""",
            (
                tenant_id,
                tenant_id,
                domain,
                domain,
                domain,
                tenant_id,
                tenant_id,
                tenant_id,
                tenant_id,
            ),
        ).fetchall()
        return [str(row["id"]) for row in rows]

    def get_fact(self, fact_id: str, tenant_id: str = "") -> dict | None:
        row = self.conn.execute(
            """SELECT * FROM facts
               WHERE id = ?
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (fact_id, tenant_id, tenant_id),
        ).fetchone()
        if row is None:
            return None
        return self._hydrate_fact_row(row)

    def get_latest_version(self, key: str, tenant_id: str = "") -> int:
        row = self.conn.execute(
            """SELECT MAX(version) as max_v FROM facts
               WHERE key = ?
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (key, tenant_id, tenant_id),
        ).fetchone()
        return row["max_v"] or 0

    def invalidate_fact(
        self,
        fact_id: str,
        reason: str,
        invalidated_at: str,
        tenant_id: str = "",
    ) -> bool:
        cur = self.conn.execute(
            """UPDATE facts SET invalidated_at = ?, invalidation_reason = ?
               WHERE id = ?
                 AND invalidated_at IS NULL
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (invalidated_at, reason, fact_id, tenant_id, tenant_id),
        )
        self._maybe_commit()
        return cur.rowcount > 0

    def get_facts_by_key(self, key: str, tenant_id: str = "") -> list[dict]:
        """Get all versions of facts for a key (including invalidated)."""
        rows = self.conn.execute(
            """SELECT * FROM facts
               WHERE key = ?
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)
               ORDER BY version""",
            (key, tenant_id, tenant_id),
        ).fetchall()
        return [self._hydrate_fact_row(row) for row in rows]

    def get_facts_by_ids(self, fact_ids: list[str], tenant_id: str = "") -> list[dict]:
        if not fact_ids:
            return []
        fact_ids_json = json.dumps(fact_ids)
        rows = self.conn.execute(
            """SELECT * FROM facts
               WHERE id IN (SELECT value FROM json_each(?))
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (fact_ids_json, tenant_id, tenant_id),
        ).fetchall()
        return [self._hydrate_fact_row(row) for row in rows]

    def list_current_facts_by_rule_family(
        self,
        rule_family: str,
        version: str,
        tenant_id: str = "",
    ) -> list[dict]:
        tenant_id = self._require_tenant_scope(tenant_id)
        rows = self.conn.execute(
            """SELECT * FROM facts
               WHERE invalidated_at IS NULL
                 AND rule_id = ?
                 AND rule_version = ?
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (rule_family, version, tenant_id, tenant_id),
        ).fetchall()
        return [self._hydrate_fact_row(row) for row in rows]

    def update_fact_rule_version(self, fact_id: str, to_version: str, tenant_id: str = "") -> bool:
        tenant_id = self._require_tenant_scope(tenant_id)
        cur = self.conn.execute(
            """UPDATE facts
               SET rule_version = ?
               WHERE id = ?
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (to_version, fact_id, tenant_id, tenant_id),
        )
        self._maybe_commit()
        return cur.rowcount > 0

    def mark_facts_stale(self, fact_ids: list[str], tenant_id: str = "") -> int:
        if not fact_ids:
            return 0
        tenant_id = self._require_tenant_scope(tenant_id)
        fact_ids_json = json.dumps(fact_ids)
        cur = self.conn.execute(
            """UPDATE facts
               SET stale = 1
               WHERE id IN (SELECT value FROM json_each(?))
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (fact_ids_json, tenant_id, tenant_id),
        )
        self._maybe_commit()
        return cur.rowcount

    def register_rule_version(self, rule_family: str, version: str, active: bool) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO rule_registry (rule_family, version, active, created_at)
               VALUES (?, ?, ?, (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')))""",
            (rule_family, version, 1 if active else 0),
        )
        self._maybe_commit()

    def set_rule_version_active(self, rule_family: str, version: str, active: bool) -> None:
        self.conn.execute(
            "UPDATE rule_registry SET active = ? WHERE rule_family = ? AND version = ?",
            (1 if active else 0, rule_family, version),
        )
        self._maybe_commit()

    def get_active_rule_versions(self, rule_family: str) -> list[str]:
        rows = self.conn.execute(
            "SELECT version FROM rule_registry WHERE rule_family = ? AND active = 1",
            (rule_family,),
        ).fetchall()
        return [str(row["version"]) for row in rows]
