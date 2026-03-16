# Integration Guide

## Transport modes

Lore supports two server transports:

- `streamable-http`: production default.
- `stdio`: development-only, enabled with `LORE_ALLOW_STDIO_DEV=1`.

## Authentication

- Lore verifies bearer tokens with the configured OIDC or HS256 settings.
- Required scopes are enforced per tool.
- Authorization failures surface as protocol errors rather than JSON tool payloads.

## Tenant isolation

- Single-tenant mode defaults requests into `default`.
- Multi-tenant mode requires a resolved tenant in auth claims or validated request context.
- Cross-tenant reads and writes are denied.

## Encryption

- High and restricted payloads can be encrypted at rest.
- Encryption is fail-closed if passphrase configuration is incomplete.
- Key rotation support is versioned through the runtime keyring.

## Embeddings

- Supported providers include `hash-local` and `openai`.
- Retrieval and backfill flows continue to use the same `ContextPackBuilder(db)` constructor.

## Typical HTTP deployment

1. Set `LORE_TRANSPORT=streamable-http`.
2. Configure OIDC verification settings.
3. Configure tenant and encryption settings if required.
4. Start `python -m lore.server`.

## Typical local MCP client setup

1. Set `LORE_TRANSPORT=stdio`.
2. Set `LORE_ALLOW_STDIO_DEV=1`.
3. Point the MCP client to `python -m lore.server`.

