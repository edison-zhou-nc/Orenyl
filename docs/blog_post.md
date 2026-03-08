# Shipping Lore v2: Contract-First Governed Memory

Lore v2 introduces a contract-first memory layer with six MCP tools, multi-domain support, and auditable deletion guarantees.

## What Changed
- Six-tool MCP contract with explicit signatures.
- Multi-domain ingestion and retrieval.
- Soft/hard delete with proof checks.
- TTL sweep and policy hooks.
- Domain export and summary derivation.
- v2.1 retrieval upgrades: optional semantic dedup + hybrid ranking fallback.
- Security upgrades: Argon2id key derivation and optional high/restricted payload encryption.

## Why It Matters
This release keeps the central invariant intact: deleted information cannot resurface. At the same time, it expands practical deployment options for agent ecosystems that need portability and governance.

## Demo Path
Run `py scripts/demo_v2.py` for a short walkthrough of store -> derive -> retrieve -> delete.
