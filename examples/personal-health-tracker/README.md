# Personal Health Tracker

Demonstrates Orenyl's memory model with health events, single-record deletion, and deletion verification.

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
python examples/personal-health-tracker/health_tracker.py
```

## From this directory

```bash
python health_tracker.py
```

## Expected output

1. Store health observations such as medications and notes.
2. Retrieve relevant health context by query.
3. Delete a specific health record with verification proof.
4. Verify that deleted allergy content does not resurface in future queries.

Look for lines similar to:

```text
Stored event:health:1: derived ...
--- Deleting allergy record with proof ---
Deletion verified: True
Deleted allergy content does not resurface.
```
