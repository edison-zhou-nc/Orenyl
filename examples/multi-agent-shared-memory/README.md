# Multi-Agent Shared Memory

Demonstrates tenant isolation: two agents share the same Lore instance but cannot see each other's tenant-scoped memory.

## Run

```bash
pip install orenyl-mcp-server   # or: pip install -e ../..
python shared_memory.py
```

## What It Shows

1. Agent A stores tenant-scoped memory for `team-alpha`.
2. Agent B stores tenant-scoped memory for `team-beta`.
3. Each agent retrieves only its own tenant's facts.
4. Queries never reveal the other tenant's underlying content.
