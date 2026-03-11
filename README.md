# Lore

![Lore social preview](docs/assets/lore_social_preview.png)

Compliance-grade memory MCP server for AI agents, with deterministic deletion and auditable lineage.

Lore gives agents durable memory without losing control: every derived fact is traceable to source events, and deletion triggers recomputation with verification.

## Why Lore

- Deterministic memory model: immutable events, derived facts, lineage edges.
- Deletion guarantees: cascade invalidation + recompute + verification proof.
- Compliance-oriented: audit traces, sensitivity controls, export workflows.
- MCP-native: stable six-tool contract for agent integration.

## Architecture

Lore stores:

- `events`: immutable user memory inputs.
- `facts`: deterministic derivations from active events.
- `edges`: lineage graph (`event -> fact`).
- `tombstones/audit`: deletion and security decision records.

Core invariant: if upstream data is deleted, downstream derivations must not resurface.

## Install

```bash
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python -m pip install -e .
```

## Quickstart (MCP Integrators)

1. Start Lore server:

```bash
python -m lore.server
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

3. Basic flow:
- `store_event`
- `retrieve_context_pack`
- `delete_and_recompute`
- `audit_trace`

## MCP Tool Contract (v2)

1. `store_event(domains, content, sensitivity, consent_source, expires_at, metadata, type?, payload?, source?, ts?)`
2. `retrieve_context_pack(domain, query, include_summary, max_sensitivity, limit, agent_id?, session_id?)`
3. `delete_and_recompute(target_id, target_type, reason, mode, run_vacuum?)`
4. `audit_trace(item_id, include_source_events=False)`
5. `list_events(domain, limit=50, offset=0, include_tombstoned=False)`
6. `export_domain(domain, format=json|markdown|timeline, confirm_restricted=False)`

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

- AuthZ is scope-based per tool action.
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
python run_eval.py
```

Run Phase 1 synthetic retrieval regression benchmark:

```bash
python -m pytest tests/benchmarks/test_phase1_retrieval_quality.py -q
```

## Contributing

See `CONTRIBUTING.md`.

## License

MIT. See `LICENSE`.
