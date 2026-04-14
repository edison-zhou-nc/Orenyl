# Migration Guide

## Scope

This release candidate preserves public import stability while hardening the internal structure toward 1.0.

## Stable imports

- `from orenyl.db import Database` is unchanged.
- `from orenyl import server` is unchanged.
- Existing `orenyl.server.handle_*` imports remain valid.

## Internal refactors

- `Database` now composes repository mixins from `orenyl.repositories`.
- MCP handlers now live in `orenyl.handlers`.
- Tool schemas and FastMCP registration are centralized in `orenyl.handlers.tooling`.

## Schema migration

- Orenyl still auto-migrates SQLite schema changes on startup.
- Existing databases are upgraded in place.
- Tenant, rule-version, consent, and DR tables remain startup-managed.

## Operational changes

- The current MCP surface is 14 tools.
- `handle_metrics` and `handle_health` remain import-compatible diagnostics, but they are not registered MCP tools.
- Health output is now structured for CI gating.

## Environment notes

Recent additions and important settings include:

- `ORENYL_TRANSPORT`
- `ORENYL_ALLOW_STDIO_DEV`
- `ORENYL_MAX_CONTEXT_PACK_LIMIT`
- `ORENYL_MAX_LIST_EVENTS_LIMIT`
- `ORENYL_TTL_DELETE_MODE`
- `ORENYL_TTL_SWEEP_INTERVAL_SECONDS`
- `ORENYL_ENABLE_MULTI_TENANT`
- `ORENYL_ENCRYPTION_PASSPHRASE`
- `ORENYL_ENCRYPTION_SALT`
- `ORENYL_OIDC_*`

## Recommended rollout

1. Upgrade in a staging environment first.
2. Start the server once to allow auto-migration to complete.
3. Run the unit and integration suite.
4. Validate your auth, transport, encryption, and tenant settings before production traffic.

