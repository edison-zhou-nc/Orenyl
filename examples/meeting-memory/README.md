# Meeting Memory

Demonstrates Orenyl's lineage tracking: store meeting notes, derive facts, and trace where each fact came from.

## Prerequisites

```bash
python -m pip install -e .
```

Once `0.5.0` is published on PyPI, you can swap that install step for:

```bash
pip install orenyl-mcp-server
```

## From the repo root

```bash
python examples/meeting-memory/meeting_memory.py
```

## From this directory

```bash
python meeting_memory.py
```

## Expected output

1. Store meeting notes as events.
2. Derive a work summary from those notes.
3. Trace the summary fact back to its source meetings.
4. Delete a meeting and watch the summary recompute without it.

Look for lines similar to:

```text
Meeting event:meeting:standup-mon: derived ...
Summary before deletion: ...
Deletion verified: True
Deleted meeting removed from summary: True
```
