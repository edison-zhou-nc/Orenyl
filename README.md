# Lore

[![CI](https://github.com/edison-zhou-nc/Lore/actions/workflows/ci.yml/badge.svg)](https://github.com/edison-zhou-nc/Lore/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/lore-mcp)](https://pypi.org/project/lore-mcp/)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
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
pip install lore-mcp
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
LORE_TRANSPORT=stdio LORE_ALLOW_STDIO_DEV=1 python -m lore.server
```

2. Configure your MCP client:

```json
{
  "mcpServers": {
    "lore": {
      "command": "python",
      "args": ["-m", "lore.server"],
      "env": {
        "LORE_TRANSPORT": "stdio",
        "LORE_ALLOW_STDIO_DEV": "1",
        "LORE_DB_PATH": "./lore_memory.db"
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

Use `streamable-http` with authenticated bearer tokens for real deployments.

1. Set `LORE_TRANSPORT=streamable-http`.
2. Configure OIDC or HS256 verification settings.
3. Start `python -m lore.server`.
4. Treat stdio mode as development only.

## MCP Tool Contract (v2)

1. `store_event(domains, content, sensitivity, consent_source, expires_at, metadata, type?, payload?, source?, ts?)`
2. `retrieve_context_pack(domain, query, include_summary, max_sensitivity, limit, agent_id?, session_id?)`
3. `delete_and_recompute(target_id, target_type, reason, mode, run_vacuum?)`
4. `audit_trace(item_id, include_source_events=False)`
5. `list_events(domain, limit=50, offset=0, include_tombstoned=False)`
6. `export_domain(domain, format=json|markdown|timeline, confirm_restricted=False)`
   - also supports `page_size`, `cursor`, `stream`, and `include_hashes`
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
| `LORE_DB_PATH` | `lore_memory.db` | SQLite database path |
| `LORE_TRANSPORT` | `streamable-http` | Server transport mode |
| `LORE_ALLOW_STDIO_DEV` | `0` | Allow stdio transport in dev |
| `LORE_MAX_CONTEXT_PACK_LIMIT` | `100` | Upper bound for context retrieval |
| `LORE_MAX_LIST_EVENTS_LIMIT` | `200` | Upper bound for list_events |
| `LORE_ENABLE_SEMANTIC_DEDUP` | `0` | Enable semantic duplicate suppression |
| `LORE_SEMANTIC_DEDUP_THRESHOLD_DEFAULT` | `0.92` | Default cosine threshold for semantic dedup |
| `LORE_SEMANTIC_DEDUP_THRESHOLD_<DOMAIN>` | unset | Domain-specific dedup threshold override (example: `..._HEALTH`) |
| `LORE_MIN_FACT_CONFIDENCE` | `0.7` | Minimum confidence required for facts in context packs |
| `LORE_EMBEDDING_PROVIDER` | `hash-local` | Embedding provider (`hash-local` or `openai`) |
| `LORE_EMBEDDING_DIM` | `128` | Vector dimension for `hash-local` provider only (ignored for `openai`) |
| `LORE_OPENAI_API_KEY` | unset | OpenAI API key for `openai` embedding provider |
| `LORE_EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model when provider is `openai` |
| `LORE_ENCRYPTION_PASSPHRASE` | unset | Enables encryption for high/restricted payloads |
| `LORE_ENCRYPTION_SALT` | unset | Base64 salt for key derivation |
| `LORE_ALLOW_INSECURE_DEV_SALT` | `0` | Dev-only fallback when salt is unset |
| `LORE_TTL_DELETE_MODE` | `soft` | TTL cleanup deletion mode |
| `LORE_TTL_SWEEP_INTERVAL_SECONDS` | `3600` | TTL sweep interval |
| `LORE_OIDC_ISSUER` | unset | OIDC token issuer (required when RS256/JWKS is enabled) |
| `LORE_OIDC_AUDIENCE` | `lore` | OIDC audience |
| `LORE_OIDC_ALLOWED_ALGS` | `RS256` | Allowed JWT algorithms; default requires issuer config |
| `LORE_OIDC_HS256_SECRET` | unset | HS256 verifier secret (required when `HS256` is enabled) |
| `LORE_OIDC_JWKS_URL` | unset | JWKS endpoint for RS256 verification |

Notes:
- With default `LORE_OIDC_ALLOWED_ALGS=RS256`, startup requires `LORE_OIDC_ISSUER` (and typically `LORE_OIDC_JWKS_URL`).
- HS256-only deployments should explicitly set `LORE_OIDC_ALLOWED_ALGS=HS256`, `LORE_OIDC_HS256_SECRET`, and `LORE_OIDC_ISSUER`.

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
LORE_ENABLE_PHASE3_LOAD_TEST=1 LORE_PHASE3_LOAD_EVENTS=1000000 python -m pytest tests/benchmarks/test_phase3_multi_tenant_load.py -q
```

## Contributing

See `CONTRIBUTING.md`.

## License

Apache-2.0. See `LICENSE`.
