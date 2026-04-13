# Show HN

## Proposed Title

Show HN: Orenyl - Governed memory for MCP agents with deletion proof

## Link Target

Link directly to the GitHub repository, not a marketing page.

## Post Goal

Frame Orenyl as a technical product for builders:
- traceable memory
- auditable derivation
- deletion verification
- non-resurfacing proof

## Prepared First Comment

I built Orenyl because I wanted agent memory with stronger guarantees than generic persistence.

The core proof flow is:

1. store a sensitive event
2. retrieve derived context
3. inspect lineage back to the source event
4. delete the source event
5. verify the deleted content does not resurface

That is the main idea:

Vector stores remember. Orenyl governs.

It is an MCP-native memory server for builders who care about high-trust workflows, not a hosted SaaS product and not an enterprise-certification claim.

The repo includes:
- quickstart
- health-style proof demo
- lineage / deletion examples
- authenticated `streamable-http` deployment path

Happy to answer questions about why this exists, why deleting rows is not enough, and where the current limits still are.

## Likely Questions To Prepare For

- Why not just delete rows?
- Why not use a vector database?
- What happens with embeddings after deletion?
- Why MCP?
- How production-ready is this really?
- What are the scale limits right now?
