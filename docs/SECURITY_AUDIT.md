# Security Audit

## Scope

This document summarizes the GA security posture of Lore's current release candidate and the checks that are enforced in CI.

## Auth coverage

- All MCP-dispatched tools enter through the authenticated `server.call_tool` flow.
- Tool authorization is scope-based and enforced before handler execution.
- Cross-tenant requests are denied when multi-tenant mode is enabled.
- Security allow and deny decisions are audit logged with request correlation.

## Encryption fail-closed behavior

- High and restricted payload encryption is optional, but when enabled it is fail-closed.
- Incomplete passphrase or salt configuration blocks secure operation instead of silently downgrading protection.
- Key-versioned encryption material is supported through the runtime keyring.

## Config hygiene

- OIDC and HS256 configuration parsing is validated at startup.
- Transport mode validation blocks unsafe stdio usage outside explicit development mode.
- Read-only mode and compliance strict mode are environment-driven and tested.

## CI controls

- CI runs Ruff correctness checks plus focused security selections.
- The current CI security lint selection includes `S105`, `S324`, `S603`, `S607`, and `S608`.
- CI also runs auth, tenant isolation, encryption misconfiguration, and perf/health gate tests.

## Remaining work

- External penetration testing is still pending.
- Secret scanning and dependency-vulnerability reporting are not yet documented as separate release gates.
- Formal threat modeling for operator deployments should be added before broader enterprise rollout.
