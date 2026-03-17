# Migration Guide

## Scope

This release candidate preserves public import stability while hardening the internal structure for GA.

## Stable imports

- `from lore.db import Database` is unchanged.
- `from lore import server` is unchanged.
- Existing `lore.server.handle_*` imports remain valid.

## Internal refactors

- `Database` now composes repository mixins from `lore.repositories`.
- MCP handlers now live in `lore.handlers`.
- Tool schemas and FastMCP registration are centralized in `lore.handlers.tooling`.

## Schema migration

- Lore still auto-migrates SQLite schema changes on startup.
- Existing databases are upgraded in place.
- Tenant, rule-version, consent, and DR tables remain startup-managed.

## Operational changes

- The current MCP surface is 14 tools.
- `handle_metrics` and `handle_health` remain import-compatible diagnostics, but they are not registered MCP tools.
- Health output is now structured for CI gating.

## Environment notes

Recent additions and important settings include:

- `LORE_TRANSPORT`
- `LORE_ALLOW_STDIO_DEV`
- `LORE_MAX_CONTEXT_PACK_LIMIT`
- `LORE_MAX_LIST_EVENTS_LIMIT`
- `LORE_TTL_DELETE_MODE`
- `LORE_TTL_SWEEP_INTERVAL_SECONDS`
- `LORE_ENABLE_MULTI_TENANT`
- `LORE_ENCRYPTION_PASSPHRASE`
- `LORE_ENCRYPTION_SALT`
- `LORE_OIDC_*`

## Recommended rollout

1. Upgrade in a staging environment first.
2. Start the server once to allow auto-migration to complete.
3. Run the unit and integration suite.
4. Validate your auth, transport, encryption, and tenant settings before production traffic.

