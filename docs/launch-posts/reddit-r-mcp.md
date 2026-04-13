# Reddit Post For r/mcp

## Title

Orenyl: governed memory for MCP agents with deletion proof and audit trace

## Body

I built Orenyl, an MCP memory server focused on governed memory rather than generic persistence.

The core behavior is:
- store a sensitive event
- retrieve derived context
- inspect the lineage / audit trace
- delete the source event
- verify the deleted content does not resurface

That last step is the differentiator for me.

Vector stores remember. Orenyl governs.

I wanted a memory layer where derived facts stay traceable to source events, and deletion triggers recomputation with verification proof instead of just row removal.

Current positioning:
- public beta / early production
- local-first evaluation
- authenticated `streamable-http` path for production deployments

If you want to try it:
- quickstart in the repo
- demo script: `python scripts/demo_health_marketing.py`

Happy to share the reasoning, tradeoffs, and where the current limits still are.
