# Lore

[![CI](https://github.com/edison-zhou-nc/Lore/actions/workflows/ci.yml/badge.svg)](https://github.com/edison-zhou-nc/Lore/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/orenyl-mcp-server)](https://pypi.org/project/orenyl-mcp-server/)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

![Lore social preview](docs/assets/lore_social_preview.png)

production-minded governed memory MCP server for AI agents, with deterministic deletion and auditable lineage.

Lore gives agents durable memory without losing control: every derived fact is traceable to source events, and deletion triggers recomputation with verification proof.

**Core guarantee:** if upstream data is deleted, downstream derivations must not resurface.

Lore is ready for self-serve local development and evaluation. Production deployments should use authenticated `streamable-http`; Lore is not yet externally certified or enterprise-complete.

## Why Lore

- **Deterministic memory model** - immutable events, derived facts, lineage edges
- **Deletion guarantees** - cascade invalidation plus recompute plus verification proof
- **Compliance-oriented** - GDPR Article 17/20/30, audit traces, sensitivity controls
- **MCP-native** - stable 14-tool contract for agent integration
- **Local-first onboarding** - explicit stdio development mode for self-serve setup and demos

## Install

```bash
pip install orenyl-mcp-server
```

Or from source:

```bash
git clone https://github.com/edison-zhou-nc/Lore.git
cd Lore
python -m pip install -e .
python -m pip install -r requirements-dev.txt
```

## Get Started

- [5-Minute Quickstart](docs/quickstart.md) - try Lore locally in minutes
- [Claude Code Integration](docs/guides/claude-code.md)
- [OpenClaw Integration](docs/guides/openclaw.md)
- [Examples](examples/) - health tracker, meeting memory, multi-agent isolation

## Architecture

Lore stores:

- `events`: immutable user memory inputs.
- `facts`: deterministic derivations from active events.
- `edges`: lineage graph (`event -> fact`).
- `tombstones/audit`: deletion and security decision records.

Core invariant: if upstream data is deleted, downstream derivations must not resurface.

## Local development mode

Use this mode for self-serve evaluation, local MCP clients, and demos. It is development only.

1. Start Lore in local stdio mode:

```bash
ORENYL_TRANSPORT=stdio ORENYL_ALLOW_STDIO_DEV=1 python -m orenyl.server
```

2. Configure your MCP client:

```json
{
  "mcpServers": {
    "lore": {
      "command": "python",
      "args": ["-m", "orenyl.server"],
      "env": {
        "ORENYL_TRANSPORT": "stdio",
        "ORENYL_ALLOW_STDIO_DEV": "1",
        "ORENYL_DB_PATH": "./lore_memory.db"
      }
    }
  }
}
```

This mode uses Lore's explicit local-dev auth bypass so you do not need external OIDC setup for local evaluation.

3. Basic flow:
- `store_event`
- `retrieve_context_pack`
- `delete_and_recompute`
- `audit_trace`

## Production deployment mode

Use `streamable-http` with authenticated tool calls for real deployments.

1. Set `ORENYL_TRANSPORT=streamable-http`.
2. Configure OIDC or HS256 verification settings.
3. Pass a JWT per tool call using `auth_token` on FastMCP-registered tools or `_auth_token` in raw tool arguments.
4. Start `orenyl-server` or `python -m orenyl.server`.
5. Treat stdio mode as development only.

Lore does not currently read an HTTP `Authorization` header inside tool dispatch. If you need gateway-level HTTP auth, terminate that at your proxy or application edge and still pass the JWT into the tool call contract described in [docs/INTEGRATION.md](docs/INTEGRATION.md).

## MCP Tool Contract (v2)

Authenticated transports use the same 14-tool contract below. When auth is enabled, include `auth_token` on FastMCP-registered tools or `_auth_token` in raw tool arguments.

1. `store_event(domains, content, sensitivity, consent_source, expires_at, metadata, type?, payload?, source?, ts?)`
2. `retrieve_context_pack(domain, query, include_summary, max_sensitivity, limit, agent_id?, session_id?)`
3. `delete_and_recompute(target_id, target_type, reason, mode, run_vacuum?)`
4. `audit_trace(item_id, include_source_events=False)`
5. `list_events(domain, limit=50, offset=0, include_tombstoned=False)`
6. `export_domain(domain, format=json|markdown|timeline, confirm_restricted=False)`
   - also supports `page_size`, `cursor`, `stream`, and `include_hashes`
   - pagination/streaming performs a full server-side load before slicing; domains with more than 10,000 events return `{"error": "export_domain_too_large_for_pagination"}`
7. `erase_subject_data(subject_id, mode=hard|soft, reason=subject_erasure)`
8. `export_subject_data(subject_id)`
9. `record_consent(subject_id, status, purpose?, legal_basis?, source?, metadata?)`
10. `generate_processing_record()`
11. `audit_anomaly_scan(window_minutes?, limit?)`
12. `create_snapshot(label?)`
13. `verify_snapshot(snapshot_id)`
14. `restore_snapshot(snapshot_id)`

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `ORENYL_DB_PATH` | `lore_memory.db` | SQLite database path |
| `ORENYL_AUDIT_DB_PATH` | `lore_audit.db` | SQLite audit log database path |
| `ORENYL_DR_SNAPSHOT_DIR` | `lore_snapshots` | Directory used for disaster recovery snapshots |
| `ORENYL_TRANSPORT` | `streamable-http` | Server transport mode |
| `ORENYL_ALLOW_STDIO_DEV` | `0` | Allow stdio transport in dev |
| `ORENYL_MAX_CONTEXT_PACK_LIMIT` | `100` | Upper bound for context retrieval |
| `ORENYL_MAX_LIST_EVENTS_LIMIT` | `200` | Upper bound for list_events |
| `ORENYL_READ_ONLY_MODE` | `0` | Reject mutating tools while keeping read-safe tools available |
| `ORENYL_RATE_LIMIT_RPM` | `100` | Per-tenant request budget; `0` disables rate limiting |
| `ORENYL_COMPLIANCE_STRICT_MODE` | `1` | Tighten compliance behavior for restricted or incomplete requests |
| `ORENYL_ENABLE_MULTI_TENANT` | `0` | Enable tenant-aware request resolution and isolation checks |
| `ORENYL_ENABLE_AGENT_PERMISSIONS` | `0` | Enforce domain-scoped policy checks for authenticated agents |
| `ORENYL_POLICY_SHADOW_MODE` | `0` | Log policy denies without enforcing them; unsafe with some agent-permission combinations |
| `ORENYL_ENABLE_SEMANTIC_DEDUP` | `0` | Enable semantic duplicate suppression |
| `ORENYL_SEMANTIC_DEDUP_THRESHOLD_DEFAULT` | `0.92` | Default cosine threshold for semantic dedup |
| `ORENYL_SEMANTIC_DEDUP_THRESHOLD_<DOMAIN>` | unset | Domain-specific dedup threshold override (example: `..._HEALTH`) |
| `ORENYL_MIN_FACT_CONFIDENCE` | `0.7` | Minimum confidence required for facts in context packs |
| `ORENYL_EMBEDDING_PROVIDER` | `hash-local` | Embedding provider (`hash-local` or `openai`) |
| `ORENYL_VECTOR_BACKEND` | `local` | Vector storage backend (`local`, `sqlite`, or `pgvector`) |
| `ORENYL_PGVECTOR_DSN` | unset | PostgreSQL DSN used when `ORENYL_VECTOR_BACKEND=pgvector` |
| `ORENYL_EMBEDDING_DIM` | `128` | Vector dimension for `hash-local` provider only (ignored for `openai`) |
| `ORENYL_EMBEDDING_WORKERS` | `4` | Worker count for async embedding tasks, clamped to 1-16 |
| `ORENYL_OPENAI_API_KEY` | unset | OpenAI API key for `openai` embedding provider |
| `ORENYL_EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model when provider is `openai` |
| `ORENYL_EMBEDDING_TIMEOUT_SECONDS` | `10` | Timeout before retrieval falls back when embeddings stall |
| `ORENYL_ENCRYPTION_PASSPHRASE` | unset | Enables encryption for high/restricted payloads |
| `ORENYL_ENCRYPTION_SALT` | unset | Base64 salt for key derivation |
| `ORENYL_ENCRYPTION_KEY_VERSION` | `v1` | Active encryption key version stamped onto encrypted payloads |
| `ORENYL_ALLOW_INSECURE_DEV_SALT` | `0` | Dev-only fallback when salt is unset |
| `ORENYL_TTL_DELETE_MODE` | `soft` | TTL cleanup deletion mode |
| `ORENYL_TTL_SWEEP_INTERVAL_SECONDS` | `3600` | TTL sweep interval |
| `ORENYL_OIDC_ISSUER` | unset | OIDC token issuer (required when RS256/JWKS is enabled) |
| `ORENYL_OIDC_AUDIENCE` | `lore` | OIDC audience |
| `ORENYL_OIDC_ALLOWED_ALGS` | `RS256` | Allowed JWT algorithms; default requires issuer config |
| `ORENYL_OIDC_HS256_SECRET` | unset | HS256 verifier secret (required when `HS256` is enabled) |
| `ORENYL_OIDC_JWKS_URL` | unset | JWKS endpoint for RS256 verification |
| `ORENYL_OIDC_JWKS_CACHE_TTL_SECONDS` | `300` | JWKS cache lifetime for RS256 verification |
| `ORENYL_OIDC_CLOCK_SKEW_SECONDS` | `30` | Allowed token clock skew in seconds |
| `ORENYL_FEDERATION_NODE_ID` | `node-local` | Stable node identifier for federation journals and conflict resolution |

Notes:
- With default `ORENYL_OIDC_ALLOWED_ALGS=RS256`, startup requires `ORENYL_OIDC_ISSUER` (and typically `ORENYL_OIDC_JWKS_URL`).
- HS256-only deployments should explicitly set `ORENYL_OIDC_ALLOWED_ALGS=HS256`, `ORENYL_OIDC_HS256_SECRET`, and `ORENYL_OIDC_ISSUER`.
- Multi-version key rotation can use `ORENYL_ENCRYPTION_PASSPHRASE_<VERSION>` and `ORENYL_ENCRYPTION_SALT_<VERSION>` alongside `ORENYL_ENCRYPTION_KEY_VERSION`.

## Security Notes

- Local stdio development mode uses an explicit local-dev auth bypass.
- AuthZ is scope-based per tool action in authenticated transports.
- Security decisions are audit-logged (allow/deny + request correlation).
- High/restricted payload encryption is fail-closed when passphrase is set without salt.
- Deletion proof includes resurface-prevention checks (`deletion_verified`).

## Development

- Code layout: `src/lore/`
- Tests: `tests/unit/`, `tests/integration/`
- Linting: Ruff + Black configured in `pyproject.toml`

Run tests:

```bash
python -m pytest -q
```

Run eval harness:

```bash
python scripts/run_eval.py
```

Run Phase 1 synthetic retrieval regression benchmark:

```bash
python -m pytest tests/benchmarks/test_phase1_retrieval_quality.py -q
```

Run Phase 3 cross-tenant isolation suite:

```bash
python -m pytest tests/integration/test_phase3_tool_isolation.py -q
```

Run Phase 3 federation suite:

```bash
python -m pytest tests/integration/test_federation_worker_idempotency.py tests/integration/test_federation_conflict_resolution.py -q
```

Run Phase 3 multi-tenant load harness (opt-in):

```bash
ORENYL_ENABLE_PHASE3_LOAD_TEST=1 ORENYL_PHASE3_LOAD_EVENTS=1000000 python -m pytest tests/benchmarks/test_phase3_multi_tenant_load.py -q
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md),
and [SECURITY.md](SECURITY.md).

## License

Apache-2.0. See `LICENSE`.
