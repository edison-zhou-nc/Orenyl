# Integration Guide

## Transport modes

Orenyl supports two server transports:

- `streamable-http`: production default.
- `stdio`: development-only, enabled with `ORENYL_ALLOW_STDIO_DEV=1`.

## Local development mode

- Transport: `stdio`
- Required env: `ORENYL_TRANSPORT=stdio`, `ORENYL_ALLOW_STDIO_DEV=1`
- Auth behavior: Orenyl uses an explicit local-dev auth bypass for self-serve setup
- Intended use: local MCP clients, demos, evaluation, and CI/dev workflows

## Production deployment mode

- Transport: `streamable-http`
- Auth behavior: per-tool JWT authentication through `auth_token` or `_auth_token`
- Intended use: protected real deployments and non-dev integrations

## Production auth contract

Orenyl authenticates at the tool-call layer, not from an HTTP `Authorization` header inside tool dispatch.

Use one of these public entry patterns:

- FastMCP-registered tools: pass `auth_token="..."` as the tool parameter.
- Raw MCP tool arguments or direct `server.call_tool(...)`: pass `"_auth_token": "..."` in the arguments object.

FastMCP converts `auth_token` into the reserved `_auth_token` field before dispatch. Tool handlers never receive the token; Orenyl removes it before business logic runs.

### Raw MCP tool call example

```json
{
  "name": "store_event",
  "arguments": {
    "_auth_token": "eyJhbGciOiJSUzI1NiIs...",
    "domains": ["user-activity"],
    "type": "note",
    "content": "User completed onboarding"
  }
}
```

### FastMCP tool example

```python
await fast.call_tool(
    "store_event",
    {
        "auth_token": token,
        "domains": ["user-activity"],
        "type": "note",
        "content": "User completed onboarding",
    },
)
```

If you need network-edge bearer auth, terminate it at your proxy or gateway and still forward the verified JWT into Orenyl's tool-call contract.

## Authentication setup

### Step 1: Choose one JWT algorithm family

Use exactly one of:

- `RS256`: recommended for OIDC providers and production identity platforms
- `HS256`: symmetric shared-secret mode for controlled environments

Do not configure both. Orenyl fails startup if mixed algorithms are enabled together.

### Step 2: Configure environment variables

#### RS256 / OIDC example

```powershell
$env:ORENYL_TRANSPORT = "streamable-http"
$env:ORENYL_OIDC_ALLOWED_ALGS = "RS256"
$env:ORENYL_OIDC_ISSUER = "https://issuer.example.com/"
$env:ORENYL_OIDC_JWKS_URL = "https://issuer.example.com/.well-known/jwks.json"
$env:ORENYL_OIDC_AUDIENCE = "orenyl"
```

Notes:

- `ORENYL_OIDC_JWKS_URL` is required for `RS256`.
- The JWKS URL must be `https://` and resolve to a public, non-private host.

#### HS256 example

```powershell
$env:ORENYL_TRANSPORT = "streamable-http"
$env:ORENYL_OIDC_ALLOWED_ALGS = "HS256"
$env:ORENYL_OIDC_ISSUER = "https://orenyl.internal/"
$env:ORENYL_OIDC_HS256_SECRET = "replace-with-at-least-32-random-bytes"
$env:ORENYL_OIDC_AUDIENCE = "orenyl"
```

Notes:

- `ORENYL_OIDC_HS256_SECRET` must be at least 32 bytes.
- Keep the secret out of source control and rotate it like any other production credential.

### Step 3: Start the server

```powershell
$env:ORENYL_TRANSPORT = "streamable-http"
orenyl-server
```

`python -m orenyl.server` works as well.

### Step 4: Mint or obtain a token

- `RS256`: obtain a token from your OIDC provider.
- `HS256`: mint a token with the shared secret.

HS256 example:

```python
import jwt
from datetime import datetime, timedelta, timezone

secret = "replace-with-at-least-32-random-bytes"
token = jwt.encode(
    {
        "sub": "agent-1",
        "iss": "https://orenyl.internal/",
        "aud": "orenyl",
        "scope": "memory:read memory:write memory:delete compliance:write operations:read operations:write",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
    },
    secret,
    algorithm="HS256",
)
print(token)
```

## Authorization behavior

- Required scopes are enforced per tool.
- Multi-tenant mode resolves tenant context from claims or validated request context.
- Cross-tenant reads and writes are denied.
- Authorization failures surface as protocol errors rather than JSON success payloads.

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
- Orenyl shares one lazy embedding provider instance across server and retrieval flows.
- `ORENYL_EMBEDDING_WORKERS` controls the async embedding worker pool and is clamped to `1..16`.

## Typical local MCP client setup

1. Set `ORENYL_TRANSPORT=stdio`.
2. Set `ORENYL_ALLOW_STDIO_DEV=1`.
3. Point the MCP client to `orenyl-server` or `python -m orenyl.server`.
4. Treat this mode as development only.
