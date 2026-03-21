"""Event-oriented persistence methods for Database."""

from __future__ import annotations

import json
from typing import Any

from ..models import Event
from ._base import BaseMixin


class EventMixin(BaseMixin):
    def _event_domains(self, event_id: str) -> list[str]:
        return [
            row[0]
            for row in self.conn.execute(
                "SELECT domain FROM event_domains WHERE event_id = ? ORDER BY domain",
                (event_id,),
            ).fetchall()
        ]

    def _hydrate_event_row(self, row) -> dict:
        data = dict(row)
        data["payload"] = json.loads(data["payload"])
        data["metadata"] = json.loads(data["metadata"])
        data["domains"] = self._event_domains(data["id"])
        return data

    def insert_event(self, event: Event) -> str:
        self.conn.execute(
            """INSERT INTO events (
                   id, type, payload, content_hash, sensitivity, consent_source,
                   expires_at, metadata, retention_tier, archived_at, agent_id,
                   session_id, source, tenant_id, ts, valid_from, valid_to, created_at
               )
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event.id,
                event.type,
                json.dumps(event.payload),
                event.content_hash,
                event.sensitivity,
                event.consent_source,
                event.expires_at,
                json.dumps(event.metadata),
                event.metadata.get("retention_tier", "hot"),
                event.metadata.get("archived_at"),
                event.metadata.get("agent_id"),
                event.metadata.get("session_id"),
                event.source,
                event.tenant_id or event.metadata.get("tenant_id", "default"),
                event.ts,
                event.valid_from,
                event.valid_to,
                event.created_at,
            ),
        )
        for domain in event.domains:
            self.conn.execute(
                "INSERT OR IGNORE INTO event_domains (event_id, domain) VALUES (?, ?)",
                (event.id, domain),
            )
        self._maybe_commit()
        return event.id

    def get_event(self, event_id: str, tenant_id: str = "") -> dict | None:
        row = self.conn.execute(
            """SELECT * FROM events
               WHERE id = ?
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (event_id, tenant_id, tenant_id),
        ).fetchone()
        if row is None:
            return None
        return self._hydrate_event_row(row)

    def find_event_by_content_hash(self, content_hash: str, tenant_id: str = "") -> dict | None:
        if not content_hash:
            return None
        tenant_id = self._require_tenant_scope(tenant_id)
        row = self.conn.execute(
            """SELECT id FROM events
               WHERE content_hash = ?
                 AND deleted_at IS NULL
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)
               ORDER BY ts DESC LIMIT 1""",
            (content_hash, tenant_id, tenant_id),
        ).fetchone()
        if row is None:
            return None
        return self.get_event(row["id"], tenant_id=tenant_id)

    def get_active_events(self, event_type: str | None = None, tenant_id: str = "") -> list[dict]:
        if event_type:
            rows = self.conn.execute(
                """SELECT * FROM events
                   WHERE deleted_at IS NULL
                     AND type = ?
                     AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)
                   ORDER BY ts""",
                (event_type, tenant_id, tenant_id),
            ).fetchall()
        else:
            rows = self.conn.execute(
                """SELECT * FROM events
                   WHERE deleted_at IS NULL
                     AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)
                   ORDER BY ts""",
                (tenant_id, tenant_id),
            ).fetchall()
        return [self._hydrate_event_row(row) for row in rows]

    def get_active_events_by_subject(self, subject_id: str, tenant_id: str = "") -> list[dict]:
        rows = self.conn.execute(
            """SELECT *
               FROM events
               WHERE deleted_at IS NULL
                 AND json_extract(metadata, '$.subject_id') = ?
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)
               ORDER BY ts""",
            (subject_id, tenant_id, tenant_id),
        ).fetchall()
        return [self._hydrate_event_row(row) for row in rows]

    def get_active_domains_by_subject(self, subject_id: str, tenant_id: str = "") -> set[str]:
        events = self.get_active_events_by_subject(subject_id=subject_id, tenant_id=tenant_id)
        return {
            str(domain or "general")
            for event in events
            for domain in (event.get("domains") or ["general"])
        }

    def get_recent_events_in_domains(
        self,
        domains: list[str],
        since_ts: str,
        tenant_id: str = "",
    ) -> list[dict]:
        if not domains:
            return []
        domains_json = json.dumps(domains)
        rows = self.conn.execute(
            """SELECT DISTINCT e.*
               FROM events e
               JOIN event_domains ed ON ed.event_id = e.id
               WHERE e.deleted_at IS NULL
                 AND e.ts >= ?
                 AND (NULLIF(?, '') IS NULL OR COALESCE(e.tenant_id, 'default') = ?)
                 AND ed.domain IN (SELECT value FROM json_each(?))
               ORDER BY e.ts DESC""",
            (since_ts, tenant_id, tenant_id, domains_json),
        ).fetchall()
        return [self._hydrate_event_row(row) for row in rows]

    def get_all_events(self, event_type: str | None = None, tenant_id: str = "") -> list[dict]:
        tenant_id = self._require_tenant_scope(tenant_id)
        if event_type:
            rows = self.conn.execute(
                """SELECT * FROM events
                   WHERE type = ?
                     AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)
                   ORDER BY ts""",
                (event_type, tenant_id, tenant_id),
            ).fetchall()
        else:
            rows = self.conn.execute(
                """SELECT * FROM events
                   WHERE (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)
                   ORDER BY ts""",
                (tenant_id, tenant_id),
            ).fetchall()
        return [self._hydrate_event_row(row) for row in rows]

    def get_active_events_by_domains(self, domains: list[str], tenant_id: str = "") -> list[dict]:
        normalized = [domain.strip().lower() for domain in domains if domain and domain.strip()]
        if not normalized:
            return self.get_active_events(tenant_id=tenant_id)
        domains_json = json.dumps(normalized)
        rows = self.conn.execute(
            """SELECT DISTINCT e.*
                FROM events e
                JOIN event_domains ed ON ed.event_id = e.id
                WHERE e.deleted_at IS NULL
                  AND (NULLIF(?, '') IS NULL OR COALESCE(e.tenant_id, 'default') = ?)
                  AND ed.domain IN (SELECT value FROM json_each(?))
                ORDER BY e.ts""",
            (tenant_id, tenant_id, domains_json),
        ).fetchall()
        return [self._hydrate_event_row(row) for row in rows]

    def get_events_by_domains(
        self,
        domains: list[str],
        include_tombstoned: bool = False,
        tenant_id: str = "",
    ) -> list[dict]:
        normalized = [domain.strip().lower() for domain in domains if domain and domain.strip()]
        if not normalized:
            if include_tombstoned:
                rows = self.conn.execute(
                    """SELECT e.*
                       FROM events e
                       WHERE (NULLIF(?, '') IS NULL OR COALESCE(e.tenant_id, 'default') = ?)
                       ORDER BY e.ts""",
                    (tenant_id, tenant_id),
                ).fetchall()
            else:
                rows = self.conn.execute(
                    """SELECT e.*
                       FROM events e
                       WHERE e.deleted_at IS NULL
                         AND (NULLIF(?, '') IS NULL OR COALESCE(e.tenant_id, 'default') = ?)
                       ORDER BY e.ts""",
                    (tenant_id, tenant_id),
                ).fetchall()
        else:
            domains_json = json.dumps(normalized)
            if include_tombstoned:
                rows = self.conn.execute(
                    """SELECT DISTINCT e.*
                        FROM events e
                        JOIN event_domains ed ON ed.event_id = e.id
                        WHERE ed.domain IN (SELECT value FROM json_each(?))
                          AND (NULLIF(?, '') IS NULL OR COALESCE(e.tenant_id, 'default') = ?)
                        ORDER BY e.ts""",
                    (domains_json, tenant_id, tenant_id),
                ).fetchall()
            else:
                rows = self.conn.execute(
                    """SELECT DISTINCT e.*
                        FROM events e
                        JOIN event_domains ed ON ed.event_id = e.id
                        WHERE ed.domain IN (SELECT value FROM json_each(?))
                          AND e.deleted_at IS NULL
                          AND (NULLIF(?, '') IS NULL OR COALESCE(e.tenant_id, 'default') = ?)
                        ORDER BY e.ts""",
                    (domains_json, tenant_id, tenant_id),
                ).fetchall()
        return [self._hydrate_event_row(row) for row in rows]

    def count_events_by_domains(
        self,
        domains: list[str],
        include_tombstoned: bool = False,
        tenant_id: str = "",
    ) -> int:
        normalized = [domain.strip().lower() for domain in domains if domain and domain.strip()]
        if not normalized:
            if include_tombstoned:
                row = self.conn.execute(
                    """SELECT COUNT(*)
                       FROM events
                       WHERE (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
                    (tenant_id, tenant_id),
                ).fetchone()
            else:
                row = self.conn.execute(
                    """SELECT COUNT(*)
                       FROM events
                       WHERE deleted_at IS NULL
                         AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
                    (tenant_id, tenant_id),
                ).fetchone()
            return int(row[0] or 0)

        domains_json = json.dumps(normalized)
        if include_tombstoned:
            row = self.conn.execute(
                """SELECT COUNT(DISTINCT e.id)
                   FROM events e
                   JOIN event_domains ed ON ed.event_id = e.id
                   WHERE ed.domain IN (SELECT value FROM json_each(?))
                     AND (NULLIF(?, '') IS NULL OR COALESCE(e.tenant_id, 'default') = ?)""",
                (domains_json, tenant_id, tenant_id),
            ).fetchone()
        else:
            row = self.conn.execute(
                """SELECT COUNT(DISTINCT e.id)
                   FROM events e
                   JOIN event_domains ed ON ed.event_id = e.id
                   WHERE ed.domain IN (SELECT value FROM json_each(?))
                     AND e.deleted_at IS NULL
                     AND (NULLIF(?, '') IS NULL OR COALESCE(e.tenant_id, 'default') = ?)""",
                (domains_json, tenant_id, tenant_id),
            ).fetchone()
        return int(row[0] or 0)

    def list_events_page(
        self,
        domains: list[str],
        include_tombstoned: bool,
        limit: int,
        offset: int,
        tenant_id: str = "",
    ) -> list[dict]:
        safe_limit = max(1, int(limit))
        safe_offset = max(0, int(offset))
        normalized = [domain.strip().lower() for domain in domains if domain and domain.strip()]

        if not normalized:
            if include_tombstoned:
                rows = self.conn.execute(
                    """SELECT e.*
                        FROM events e
                        WHERE (NULLIF(?, '') IS NULL OR COALESCE(e.tenant_id, 'default') = ?)
                        ORDER BY e.ts
                        LIMIT ? OFFSET ?""",
                    (tenant_id, tenant_id, safe_limit, safe_offset),
                ).fetchall()
            else:
                rows = self.conn.execute(
                    """SELECT e.*
                        FROM events e
                        WHERE e.deleted_at IS NULL
                          AND (NULLIF(?, '') IS NULL OR COALESCE(e.tenant_id, 'default') = ?)
                        ORDER BY e.ts
                        LIMIT ? OFFSET ?""",
                    (tenant_id, tenant_id, safe_limit, safe_offset),
                ).fetchall()
        else:
            domains_json = json.dumps(normalized)
            if include_tombstoned:
                rows = self.conn.execute(
                    """SELECT DISTINCT e.*
                        FROM events e
                        JOIN event_domains ed ON ed.event_id = e.id
                        WHERE ed.domain IN (SELECT value FROM json_each(?))
                          AND (NULLIF(?, '') IS NULL OR COALESCE(e.tenant_id, 'default') = ?)
                        ORDER BY e.ts
                        LIMIT ? OFFSET ?""",
                    (domains_json, tenant_id, tenant_id, safe_limit, safe_offset),
                ).fetchall()
            else:
                rows = self.conn.execute(
                    """SELECT DISTINCT e.*
                        FROM events e
                        JOIN event_domains ed ON ed.event_id = e.id
                        WHERE ed.domain IN (SELECT value FROM json_each(?))
                          AND e.deleted_at IS NULL
                          AND (NULLIF(?, '') IS NULL OR COALESCE(e.tenant_id, 'default') = ?)
                        ORDER BY e.ts
                        LIMIT ? OFFSET ?""",
                    (domains_json, tenant_id, tenant_id, safe_limit, safe_offset),
                ).fetchall()

        return [self._hydrate_event_row(row) for row in rows]

    def get_event_count(self, domain: str = "general", tenant_id: str = "") -> int:
        if domain and domain != "general":
            row = self.conn.execute(
                """SELECT COUNT(DISTINCT e.id)
                   FROM events e
                   JOIN event_domains ed ON ed.event_id = e.id
                   WHERE e.deleted_at IS NULL
                     AND ed.domain = ?
                     AND (NULLIF(?, '') IS NULL OR COALESCE(e.tenant_id, 'default') = ?)""",
                (domain, tenant_id, tenant_id),
            ).fetchone()
            return int(row[0] or 0)
        row = self.conn.execute(
            """SELECT COUNT(*) FROM events
               WHERE deleted_at IS NULL
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (tenant_id, tenant_id),
        ).fetchone()
        return int(row[0] or 0)

    def get_latest_event_ts(self, domain: str = "general", tenant_id: str = "") -> str | None:
        if domain and domain != "general":
            row = self.conn.execute(
                """SELECT MAX(e.ts)
                   FROM events e
                   JOIN event_domains ed ON ed.event_id = e.id
                   WHERE e.deleted_at IS NULL
                     AND ed.domain = ?
                     AND (NULLIF(?, '') IS NULL OR COALESCE(e.tenant_id, 'default') = ?)""",
                (domain, tenant_id, tenant_id),
            ).fetchone()
            value = row[0] if row is not None else None
            return str(value) if value is not None else None
        row = self.conn.execute(
            """SELECT MAX(ts) FROM events
               WHERE deleted_at IS NULL
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (tenant_id, tenant_id),
        ).fetchone()
        value = row[0] if row is not None else None
        return str(value) if value is not None else None

    def get_expired_events(self, now_iso_ts: str, tenant_id: str = "") -> list[dict]:
        tenant_id = self._require_tenant_scope(tenant_id)
        rows = self.conn.execute(
            """SELECT * FROM events
               WHERE deleted_at IS NULL
                 AND expires_at IS NOT NULL
                 AND expires_at <= ?
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)
               ORDER BY expires_at ASC""",
            (now_iso_ts, tenant_id, tenant_id),
        ).fetchall()
        return [self._hydrate_event_row(row) for row in rows]

    def get_expired_events_global(self, now_iso_ts: str) -> list[dict]:
        rows = self.conn.execute(
            """SELECT * FROM events
               WHERE deleted_at IS NULL
                 AND expires_at IS NOT NULL
                 AND expires_at <= ?
               ORDER BY expires_at ASC""",
            (now_iso_ts,),
        ).fetchall()
        return [self._hydrate_event_row(row) for row in rows]

    def soft_delete_event(self, event_id: str, deleted_at: str, tenant_id: str = "") -> bool:
        cur = self.conn.execute(
            """UPDATE events
               SET deleted_at = ?
               WHERE id = ?
                 AND deleted_at IS NULL
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (deleted_at, event_id, tenant_id, tenant_id),
        )
        self._maybe_commit()
        return cur.rowcount > 0

    def hard_delete_event(self, event_id: str, tenant_id: str = "") -> bool:
        self.conn.execute(
            """DELETE FROM event_domains
               WHERE event_id IN (
                   SELECT id FROM events
                   WHERE id = ?
                     AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)
               )""",
            (event_id, tenant_id, tenant_id),
        )
        cur = self.conn.execute(
            """DELETE FROM events
               WHERE id = ?
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (event_id, tenant_id, tenant_id),
        )
        self._maybe_commit()
        return cur.rowcount > 0

    def update_event_payload(self, event_id: str, payload: dict[str, Any], tenant_id: str = "") -> bool:
        tenant_id = self._require_tenant_scope(tenant_id)
        cur = self.conn.execute(
            """UPDATE events
               SET payload = ?
               WHERE id = ?
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (json.dumps(payload), event_id, tenant_id, tenant_id),
        )
        self._maybe_commit()
        return cur.rowcount > 0

    def update_event_retention(
        self,
        event_id: str,
        tier: str,
        archived_at: str | None,
        tenant_id: str = "",
    ) -> bool:
        tenant_id = self._require_tenant_scope(tenant_id)
        cur = self.conn.execute(
            """UPDATE events
               SET retention_tier = ?, archived_at = ?
               WHERE id = ?
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (tier, archived_at, event_id, tenant_id, tenant_id),
        )
        self._maybe_commit()
        return cur.rowcount > 0

    def get_events_by_ids(self, event_ids: list[str], tenant_id: str = "") -> dict[str, dict]:
        if not event_ids:
            return {}
        event_ids_json = json.dumps(event_ids)
        rows = self.conn.execute(
            """SELECT * FROM events
               WHERE id IN (SELECT value FROM json_each(?))
                 AND (NULLIF(?, '') IS NULL OR COALESCE(tenant_id, 'default') = ?)""",
            (event_ids_json, tenant_id, tenant_id),
        ).fetchall()
        domain_rows = self.conn.execute(
            (
                "SELECT event_id, domain FROM event_domains "
                "WHERE event_id IN (SELECT value FROM json_each(?)) ORDER BY domain"
            ),
            (event_ids_json,),
        ).fetchall()
        domains_by_event: dict[str, list[str]] = {event_id: [] for event_id in event_ids}
        for row in domain_rows:
            domains_by_event.setdefault(row["event_id"], []).append(row["domain"])

        events: dict[str, dict] = {}
        for row in rows:
            event = dict(row)
            event["payload"] = json.loads(event["payload"])
            event["metadata"] = json.loads(event["metadata"])
            event["domains"] = domains_by_event.get(event["id"], [])
            events[event["id"]] = event
        return events
