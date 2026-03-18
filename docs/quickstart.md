# Quickstart: Lore in 5 Minutes

Get compliance-grade AI agent memory running locally with zero configuration.

## Install

```bash
pip install lore-mcp
```

Or from source:

```bash
git clone https://github.com/edison-zhou-nc/Lore.git
cd Lore
pip install -e .
```

## Try It (Python)

```python
from lore.db import Database
from lore.lineage import LineageEngine
from lore.context_pack import ContextPackBuilder
from lore.models import Event

# 1. Create an in-memory database
db = Database(":memory:")
engine = LineageEngine(db)
builder = ContextPackBuilder(db)

# 2. Store an event
event = Event(
    id="event:demo:1",
    type="note",
    payload={"text": "Started metformin 500mg daily for blood sugar"},
    domains=["health"],
    sensitivity="medium",
)
db.insert_event(event)
facts = engine.derive_facts_for_event(db.get_event(event.id))
print(f"Derived {len(facts)} fact(s)")

# 3. Retrieve a context pack
pack = builder.build(domain="health", query="medication", limit=10)
print(f"Context pack: {len(pack.facts)} fact(s)")

# 4. Delete with verification
proof = engine.delete_and_recompute(event.id, "event", reason="user_request", mode="soft")
verified = proof.to_dict()["checks"]["deletion_verified"]
print(f"Deletion verified: {verified}")

# 5. Verify nothing resurfaces
pack_after = builder.build(domain="health", query="medication", limit=10)
print(f"After deletion: {len(pack_after.facts)} fact(s)")
```

Expected output:

```text
Derived 2 fact(s)
Context pack: 2 fact(s)
Deletion verified: True
After deletion: 0 fact(s)
```

## Run as MCP Server

For AI agent integration (Claude Code, OpenClaw, etc.):

```bash
LORE_TRANSPORT=stdio LORE_ALLOW_STDIO_DEV=1 python -m lore.server
```

See [Integration Guides](guides/) for client-specific configuration.

## What Just Happened?

1. **Store**: Immutable event recorded with domain and sensitivity tags
2. **Derive**: Facts extracted deterministically from the event
3. **Retrieve**: Context pack assembled with relevance ranking and lineage tracing
4. **Delete**: Event removed, downstream facts invalidated and recomputed
5. **Verify**: Proof confirms deleted data cannot resurface

This is Lore's core guarantee: **if upstream data is deleted, downstream derivations must not resurface.**

## Next Steps

- [Claude Code Integration](guides/claude-code.md)
- [OpenClaw Integration](guides/openclaw.md) *(coming soon)*
- [MCP Tool Contract](MCP_TOOL_CONTRACTS.md) - full API reference
