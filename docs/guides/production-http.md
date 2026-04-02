# Production HTTP Deployment Template

This guide is for early-production operators who want Lore exposed over authenticated `streamable-http`. It is intentionally compact: enough to stand up a safe public-beta deployment without turning into a full infrastructure manual.

## When to use this mode

Use authenticated `streamable-http` when Lore is behind a real network boundary and tool calls must be authorized per request. Keep `stdio` for local development only.

## Required environment

At minimum, set these paths and transport settings:

- `LORE_TRANSPORT=streamable-http`
- `LORE_DB_PATH` for the primary SQLite memory store
- `LORE_AUDIT_DB_PATH` for audit and security events
- `LORE_DR_SNAPSHOT_DIR` for disaster-recovery snapshots

For authenticated deployments, also configure one JWT family:

- `LORE_OIDC_ALLOWED_ALGS=RS256` with issuer and JWKS settings for OIDC / RS256
- `LORE_OIDC_ALLOWED_ALGS=HS256` with a shared secret for controlled environments

## Example setups

### RS256 / OIDC

Use this when you already have an OIDC provider or production identity platform.

```powershell
$env:LORE_TRANSPORT = "streamable-http"
$env:LORE_OIDC_ALLOWED_ALGS = "RS256"
$env:LORE_OIDC_ISSUER = "https://issuer.example.com/"
$env:LORE_OIDC_JWKS_URL = "https://issuer.example.com/.well-known/jwks.json"
```

### HS256

Use this only when a shared secret is acceptable and you can protect it like any other production credential. The HS256 secret must be at least 32 bytes.

```powershell
$env:LORE_TRANSPORT = "streamable-http"
$env:LORE_OIDC_ALLOWED_ALGS = "HS256"
$env:LORE_OIDC_ISSUER = "https://issuer.example.com/"
$env:LORE_OIDC_HS256_SECRET = "replace-with-at-least-32-random-bytes"
```

## Data, snapshots, and backup

- Keep the primary DB and audit DB on durable storage with routine snapshots.
- Treat `LORE_DR_SNAPSHOT_DIR` as part of the recovery path, not a scratch directory.
- Back up the SQLite files and snapshot artifacts together so audit and memory state stay aligned during restore.
- If encryption is enabled, keep `LORE_ENCRYPTION_PASSPHRASE` and `LORE_ENCRYPTION_SALT` in the same secret-management flow as your JWT material.

## Operator responsibilities

- Verify the transport is `streamable-http` before exposing the service.
- Choose exactly one JWT family and rotate its secrets or keys on a defined schedule.
- Monitor the audit DB and snapshot freshness.
- Keep secrets out of source control and out of shared example configs.
- Treat this deployment as early production, not enterprise-complete.