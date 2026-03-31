# Security Audit

## Scope

This document summarizes Lore's public-launch security posture, accepted risks, and pre-release verification checks.

## Auth coverage

- All MCP-dispatched tools enter through authenticated `server.call_tool` or the FastMCP wrappers.
- Production auth uses per-tool JWT transport in the arguments object: `auth_token` for FastMCP wrappers, `_auth_token` for raw tool arguments.
- Required scopes are enforced before handler execution.
- Cross-tenant requests are denied when multi-tenant mode is enabled.
- Security allow and deny decisions are audit logged with request correlation.

## Cryptography and secrets

- High and restricted payload encryption is optional, but when enabled it is fail-closed.
- AES-GCM payloads bind envelope metadata through AAD to prevent metadata swapping.
- Incomplete encryption configuration blocks secure operation instead of silently downgrading protection.
- Key-versioned encryption material is supported through the runtime keyring.
- HS256 auth secrets must meet a 32-byte minimum.

## Config hygiene

- Mixed JWT algorithm families are rejected at startup.
- `RS256` requires a JWKS URL and Lore validates the URL as HTTPS on a public, non-private host.
- Transport mode validation blocks unsafe stdio usage outside explicit development mode.
- Read-only mode and compliance strict mode are environment-driven and tested.

## CI and release controls

- CI runs Ruff correctness checks plus focused security selections.
- The current security lint selection includes `S105`, `S324`, `S603`, `S607`, and `S608`.
- CI and release verification both run Bandit and `pip-audit`.
- CI runs auth, tenant isolation, encryption misconfiguration, and health/perf gate tests.

## Pre-review sanity check (2026-03-30)

Verified locally before requesting an independent release-readiness review:

- `python -m ruff check . --select F,B`: pass
- `python -m ruff check src --select S105,S324,S603,S607,S608`: pass
- `python -m bandit -r src/lore -ll -q`: pass
- `python -m pip_audit -r requirements.lock --disable-pip`: pass
- `python -m pip_audit -r requirements-dev.lock --disable-pip`: pass
- `python -m mypy src/lore --config-file pyproject.toml`: pass
- `python -m pytest tests/unit tests/integration -q --cov=src/lore --cov-report=term-missing --cov-fail-under=80`: pass, 405 passed / 1 skipped, 90.71% coverage
- `python -m build`: pass
- Wheel smoke import: pass

Category spot-checks covered in this pass:

- Input validation: store, consent, erasure, and export handlers validate user-controlled inputs.
- Authentication: mixed JWT algorithms are blocked, HS256 secrets are strength-checked, and RS256 requires a valid JWKS URL.
- Authorization: policy shadow mode cannot be combined with agent permissions in unsafe configurations.
- Resource bounding: oversized exports fail before materialization, latency metrics are bounded, recursive lineage queries cap depth, and retrieval-log deletion is paginated.
- Concurrency and lifecycle: federation worker initialization is locked, runtime singletons are shared, restore runs in a transaction, httpx clients are closable, and pgvector connections are reusable and closable.
- Data lifecycle: subject erasure clears consent history, schema versioning is tracked, and DR snapshot paths are validated before verification or restore.

## Accepted risks

### M3: In-memory rate limiter

Lore uses an in-memory per-tenant rate limiter. This is acceptable for single-node deployments but is not a distributed rate-limit solution.

Mitigation:

- Put a reverse proxy or API gateway in front of Lore for multi-node or internet-facing deployments.

### M4: Tenant isolation via query scoping

Lore's multi-tenant isolation model is enforced through validated tenant context plus explicit SQL query scoping. This is the chosen architecture for the current product shape, not a latent bug.

Mitigation:

- Keep tenant resolution tests in CI.
- Treat schema or repository changes that touch tenant filtering as security-sensitive review items.

### M7: CSRF

Lore is not designed as a browser session app, so CSRF is low-risk for the intended MCP usage model.

Mitigation:

- If you expose Lore behind a browser-accessible HTTP surface, terminate requests at a gateway that enforces origin, session, and anti-CSRF controls.

### M12: Event-field extraction from metadata

Lore intentionally allows event metadata to participate in domain logic where designed. This is a product choice rather than a hidden parser bug.

Mitigation:

- Keep metadata usage explicit in handler and rule review.
- Validate user-controlled metadata fields before persistence.

## Remaining work

- External penetration testing is still pending.
- Formal threat modeling for operator deployments should be expanded before broader enterprise rollout.
- Lore is not externally certified or independently validated as an enterprise security product.
