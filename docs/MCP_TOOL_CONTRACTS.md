# MCP Tool Contracts

Lore currently exposes 14 MCP-dispatched tools. In local dev stdio mode (`LORE_TRANSPORT=stdio` with `LORE_ALLOW_STDIO_DEV=1`), tool calls run under the explicit local-dev auth bypass. In authenticated transports, tool calls require a valid auth token and server-side authorization is enforced per tool.

## Common expectations

- Reads require `memory:read`.
- Writes require `memory:write`.
- Deletes require `memory:delete`.
- Exports require `memory:export`.
- Multi-tenant deployments resolve tenant scope from verified auth claims.
- Errors are returned as structured JSON payloads unless authorization fails at the transport layer.

## Tool summary

### `store_event`
- Schema: `domains` required; accepts `content`, `type`, `payload`, `sensitivity`, `consent_source`, `expires_at`, `metadata`, `source`, and `ts`.
- Auth: requires `memory:write`.
- Side effects: writes an event, may derive facts, may write embeddings, may encrypt high or restricted payloads.
- Sample response: `{"stored": true, "event_id": "event:note:...", "derived_facts": []}`.

### `retrieve_context_pack`
- Schema: accepts `domain`, `query`, `include_summary`, `max_sensitivity`, `limit`, `agent_id`, and `session_id`.
- Auth: requires `memory:read`.
- Side effects: reads current facts, may query embeddings, records audit and metrics.
- Sample response: `{"domain": "general", "facts": [], "summary": "...", "trace": {...}}`.

### `delete_and_recompute`
- Schema: requires `target_id` and `target_type`; accepts `reason`, `mode`, and `run_vacuum`.
- Auth: requires `memory:delete`.
- Side effects: writes deletion proof artifacts, tombstones, lineage recompute results, and audit entries.
- Sample response: `{"target_id": "...", "checks": {"deletion_verified": true}}`.

### `audit_trace`
- Schema: requires `item_id`; accepts `include_source_events`.
- Auth: requires `memory:read`.
- Side effects: reads lineage graph and emits audit records.
- Sample response: `{"item": {...}, "parents": [], "children": []}`.

### `list_events`
- Schema: accepts `domain`, `limit`, `offset`, and `include_tombstoned`.
- Auth: requires `memory:read`.
- Side effects: reads paginated event history and emits metrics.
- Sample response: `{"total_count": 1, "count": 1, "events": [...]}`.

### `export_domain`
- Schema: requires `domain`; accepts `format`, `confirm_restricted`, `page_size`, `cursor`, `stream`, and `include_hashes`.
- Auth: requires `memory:export`; restricted exports additionally require the restricted export capability.
- Side effects: reads events, facts, lineage edges, and may emit restricted-access audit denials.
- Sample response: `{"domain": "general", "events": [], "facts": [], "edges": [], "summary": "..."}`.

### `erase_subject_data`
- Schema: requires `subject_id`; accepts `mode` and `reason`.
- Auth: requires `memory:delete`.
- Side effects: cascades subject-linked deletion and returns verification output.
- Sample response: `{"ok": true, "deleted_event_count": 1, "deletion_verified": true}`.

### `export_subject_data`
- Schema: requires `subject_id`.
- Auth: requires `memory:export`.
- Side effects: reads subject-linked records and builds a deterministic manifest.
- Sample response: `{"ok": true, "manifest": {"record_count": 1}, "events": [], "facts": []}`.

### `record_consent`
- Schema: requires `subject_id` and `status`; accepts `purpose`, `legal_basis`, `source`, and `metadata`.
- Auth: requires `memory:write`.
- Side effects: writes a consent record and updates compliance state.
- Sample response: `{"ok": true, "record_id": "consent:..."}`.

### `generate_processing_record`
- Schema: no body fields.
- Auth: requires `memory:export`.
- Side effects: aggregates current processing metadata for the active tenant.
- Sample response: `{"tenant_id": "default", "event_count": 1, "consent_purposes": [...]}`.

### `audit_anomaly_scan`
- Schema: accepts `window_minutes` and `limit`.
- Auth: requires `memory:read`.
- Side effects: reads audit history and returns anomaly candidates.
- Sample response: `{"ok": true, "window_minutes": 60, "alerts": []}`.

### `create_snapshot`
- Schema: accepts `label`.
- Auth: requires `memory:write`.
- Side effects: creates a snapshot file and records DR metadata in the database.
- Sample response: `{"ok": true, "snapshot_id": "snapshot:manual:...", "checksum": "..."}`.

### `verify_snapshot`
- Schema: requires `snapshot_id`.
- Auth: requires `memory:read`.
- Side effects: reads stored DR metadata and computes checksum state for comparison.
- Sample response: `{"ok": true, "snapshot_id": "snapshot:manual:...", "checksum_valid": true}`.

### `restore_snapshot`
- Schema: requires `snapshot_id`.
- Auth: requires `memory:delete`.
- Side effects: replaces the active database contents from the selected snapshot.
- Sample response: `{"ok": true, "snapshot_id": "snapshot:manual:...", "restored": true}`.

## Compatibility note

`handle_metrics` and `handle_health` remain importable from `lore.server` for diagnostics, but they are intentionally not part of the MCP-dispatched tool surface.
