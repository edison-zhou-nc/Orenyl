# Architecture Decisions

## ADR 1: Preserve the `Database` import surface

The GA refactor keeps `from lore.db import Database` stable. Internal persistence moved into repository mixins to reduce file size and improve reviewability without forcing constructor churn across the codebase.

## ADR 2: Preserve `lore.server.handle_*` imports

Handler logic moved into `lore.handlers.*`, but `lore.server` still re-exports the established handler names. This keeps tests and integrators stable while allowing `server.py` to shrink.

## ADR 3: Use lazy dependency access for handlers

Handlers access runtime singletons through `lore.handlers._deps`. This is intentionally coupled to `lore.server` and favors import compatibility over fully standalone handlers.

## ADR 4: Treat decomposition as a gated invariant

The repo now has tests that enforce `db.py` and `server.py` size ceilings and verify the exported handler surface so structural regression is caught in CI.

## ADR 5: SQLite as primary storage backend

SQLite in WAL mode provides ACID transactions, zero-configuration deployment, and sub-millisecond read latency for the single-tenant use case. Write concurrency is limited to one writer at a time, which becomes a bottleneck above ~50 concurrent write agents. The migration trigger to PostgreSQL is: sustained write latency exceeding 100ms at p99 or multi-tenant isolation requirements. The storage layer is accessed through `Database` which can be abstracted behind a `StorageBackend` protocol when needed.

## ADR 6: Immutable events with derived facts

Events are append-only and never modified. Facts are deterministically derived from events and can be recomputed at any time. This event-sourcing model ensures that deletion is provable: when an event is deleted, all derived facts are invalidated, recomputed from remaining events, and a verification proof confirms no deleted data resurfaces. The tradeoff is storage overhead from keeping derivation history, which is acceptable given the compliance guarantees it enables.

## ADR 7: GDPR-first compliance architecture

Compliance is a core architectural invariant, not a bolt-on feature. Erasure (Article 17), export (Article 20), and processing records (Article 30) are built into the data model via cascade deletion, subject-scoped export, and consent lifecycle tracking. This means every data path must respect tenant isolation, sensitivity levels, and consent status. The tradeoff is additional complexity in the retrieval and storage paths, which is justified by the target market (regulated enterprise AI deployments).

## ADR 8: MCP as transport protocol

MCP (Model Context Protocol) is chosen over custom REST APIs because it provides a standardized tool-calling interface that works with any MCP-compatible AI client (Claude, OpenClaw, etc.) without custom integration code. The 14-tool contract is stable and versioned. The tradeoff is dependency on the MCP ecosystem, mitigated by the protocol being open-source (Linux Foundation) and the server also supporting stdio transport for local development.

## ADR 9: Open-core licensing boundary

The core memory model (events, facts, edges, deletion, lineage, 14-tool MCP contract, local embeddings, single-tenant SQLite, basic encryption) remains Apache-2.0-licensed. Commercial features (multi-tenant isolation, federation, external vectordb, admin dashboard, GDPR automation reports, SOC2 audit artifacts, priority support) are reserved for a paid tier. The boundary is drawn at operational complexity that enterprises need but individuals do not.

## ADR 10: Embedding provider abstraction

The `EmbeddingProvider` protocol allows swapping between deterministic hash-based embeddings (zero-config, offline, good for dev/test) and real embedding models (OpenAI, future: local transformers). This abstraction exists because embedding quality directly affects retrieval relevance, and different deployments have different constraints (air-gapped vs. cloud, cost vs. quality). The hash-local provider ensures Lore works with zero external dependencies out of the box.

