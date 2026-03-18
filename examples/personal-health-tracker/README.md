# Personal Health Tracker

Demonstrates Lore's memory model with health events, GDPR erasure, and deletion verification.

## Run

```bash
pip install lore-mcp   # or: pip install -e ../..
python health_tracker.py
```

## What It Shows

1. Store health observations such as medications and notes.
2. Retrieve relevant health context by query.
3. Delete a specific health record with verification.
4. Verify that deleted allergy content does not resurface in future queries.
