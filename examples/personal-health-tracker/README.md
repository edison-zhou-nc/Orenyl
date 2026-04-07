# Personal Health Tracker

Demonstrates Orenyl's memory model with health events, single-record deletion, and deletion verification.

## Run

```bash
pip install orenyl-mcp-server   # or: pip install -e ../..
python health_tracker.py
```

## What It Shows

1. Store health observations such as medications and notes.
2. Retrieve relevant health context by query.
3. Delete a specific health record with verification proof.
4. Verify that deleted allergy content does not resurface in future queries.
