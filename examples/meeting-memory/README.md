# Meeting Memory

Demonstrates Lore's lineage tracking: store meeting notes, derive facts, and trace where each fact came from.

## Run

```bash
pip install lore-mcp   # or: pip install -e ../..
python meeting_memory.py
```

## What It Shows

1. Store meeting notes as events.
2. Derive a work summary from those notes.
3. Trace the summary fact back to its source meetings.
4. Delete a meeting and watch the summary recompute without it.
