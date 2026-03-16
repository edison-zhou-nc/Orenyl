# MCP Tool Contracts

Lore currently exposes 14 MCP-dispatched tools. All tool calls require a valid auth token through the active server transport, and server-side authorization is enforced per tool.

## Common expectations

- Reads require `memory:read`.
- Writes require `memory:write`.
- Deletes require `memory:delete`.
- Exports require `memory:export`.
- Multi-tenant deployments resolve tenant scope from verified auth claims.
- Errors are returned as structured JSON payloads unless authorization fails at the transport layer.

## Tool summary

### `store_event`
- Purpose: persist a durable memory event.
- Key inputs: `domains`, `content`, `type`, `payload`, `sensitivity`, `consent_source`.
- Side effects: writes events, may derive facts, may encrypt restricted payloads.
- Success shape: `{"ok": true, "stored": true, ...}`.

### `retrieve_context_pack`
- Purpose: return facts, summary, and retrieval metadata for a domain.
- Key inputs: `domain`, `query`, `include_summary`, `max_sensitivity`, `limit`.
- Side effects: audit and metrics only.

### `delete_and_recompute`
- Purpose: delete an event or fact and recompute downstream lineage.
- Key inputs: `target_id`, `target_type`, `reason`, `mode`, `run_vacuum`.
- Side effects: writes tombstones, invalidates or deletes downstream data.

### `audit_trace`
- Purpose: return lineage for an event or fact.
- Key inputs: `item_id`, `include_source_events`.
- Side effects: audit only.

### `list_events`
- Purpose: page through event history.
- Key inputs: `domain`, `limit`, `offset`, `include_tombstoned`.
- Side effects: none beyond metrics and audit.

### `export_domain`
- Purpose: export events, facts, and lineage for a domain.
- Key inputs: `domain`, `format`, `confirm_restricted`.
- Formats: `json`, `markdown`, `timeline`.

### `erase_subject_data`
- Purpose: remove subject-linked active records and cascade recompute.
- Key inputs: `subject_id`, `mode`, `reason`.
- Side effects: deletion workflow and audit trail updates.

### `export_subject_data`
- Purpose: export subject-linked active records.
- Key inputs: `subject_id`.
- Success shape includes a deterministic manifest.

### `record_consent`
- Purpose: persist a consent status change.
- Key inputs: `subject_id`, `status`, `purpose`, `legal_basis`, `source`, `metadata`.

### `generate_processing_record`
- Purpose: produce an Article 30-style processing record.
- Key inputs: none.

### `audit_anomaly_scan`
- Purpose: scan audit activity for suspicious patterns.
- Key inputs: `window_minutes`, `limit`.

### `create_snapshot`
- Purpose: create a disaster recovery snapshot.
- Key inputs: `label`.

### `verify_snapshot`
- Purpose: verify snapshot integrity.
- Key inputs: `snapshot_id`.

### `restore_snapshot`
- Purpose: restore a previously created snapshot.
- Key inputs: `snapshot_id`.

## Compatibility note

`handle_metrics` and `handle_health` remain importable from `lore.server` for diagnostics, but they are intentionally not part of the MCP-dispatched tool surface.

