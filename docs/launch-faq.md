# Launch FAQ

## Who this is for

Orenyl is for AI engineers and technical founders building MCP agents or internal copilots that need governed memory for sensitive or high-trust workflows.

The best first-fit users are teams who care about:
- deletion that can be verified
- lineage from derived facts back to source events
- auditable memory operations
- local-first evaluation before production deployment

## Why not use a generic memory store or vector database?

Vector stores remember. Orenyl governs.

A generic memory layer can store rows or embeddings, but it does not automatically prove where derived facts came from or guarantee that deletion triggers recomputation with non-resurfacing verification.

Orenyl is built around that governed-memory contract.

## Why not just roll this yourself?

You can store memory in SQLite or a vector store yourself.

What Orenyl adds is the hard part:
- deterministic derivation
- lineage edges
- deletion proof
- audit traces
- a stable MCP tool contract around those behaviors

## What is the main proof to look for?

The key proof is:
- store an event
- retrieve derived context
- inspect the audit trace
- delete the source event
- confirm `deletion_verified`
- confirm the deleted content does not resurface

That is the fastest way to understand what makes Orenyl different.

## Is this local dev only or production-ready?

Local dev is the easiest way to evaluate Orenyl.

Use:
- `stdio` for local development and demos
- authenticated `streamable-http` for production deployments

The project is in public beta / early production. It is suitable for self-serve evaluation and controlled deployments, but it is not marketed as enterprise-certified or enterprise-complete.

## What does production mean here?

Production means:
- authenticated tool calls
- operator-managed deployment
- explicit runtime configuration
- audit and deletion guarantees enforced by the server

It does not mean:
- hosted SaaS
- SOC 2 certification
- external compliance certification
- every enterprise control being bundled into the repo

## Why use a health-style demo?

Sensitive health-style memory makes the value of deletion, lineage, and auditability immediately obvious.

The demo is there to show the governed-memory behavior in a high-trust setting, not to imply medical certification.

## How does multi-agent support fit in?

The hero story is deletion-proof governed memory.

Multi-agent isolation is supporting technical proof that Orenyl can also separate tenant-scoped memory and shared-memory concerns in more complex deployments.

## What should a first-time evaluator do?

1. Run the quickstart
2. Watch the health-style proof flow
3. Verify deletion proof and non-resurfacing
4. Decide whether your workflow needs governed memory rather than generic persistence

## What are the current beta limitations?

- No external certification claims
- No hosted product
- Performance and scale are honest current-state constraints, not the main story
- Some launch assets are still being refined during this first marketing wave
