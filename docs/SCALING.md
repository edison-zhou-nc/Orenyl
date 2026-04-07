# Scaling Notes

## Current target

Orenyl is optimized for SQLite with WAL enabled and deterministic local persistence.

## What scales well now

- Single-node deployments with moderate write rates.
- Tenant-scoped read and write traffic.
- Deterministic export, deletion, and audit workflows.

## Known ceilings

- SQLite write concurrency remains bounded by a single-writer model.
- Large embedding workloads and broad export jobs can compete with foreground traffic.
- Snapshot-based DR remains file-copy based.

## When to graduate

Consider a heavier deployment model when you need:

- sustained high write throughput,
- large vector search workloads,
- multi-node coordination beyond the current federation journal,
- stricter RPO/RTO expectations than local snapshots can support.

At that point, a PostgreSQL plus pgvector style architecture is the likely next step.

