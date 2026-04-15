# Multi-Agent Shared Memory

Demonstrates tenant isolation: two agents share the same Orenyl instance but cannot see each other's tenant-scoped memory.

## Prerequisites

```bash
pip install orenyl-mcp-server
```

For local development from this repo, you can use:

```bash
python -m pip install -e .
```

## From the repo root

```bash
python examples/multi-agent-shared-memory/shared_memory.py
```

## From this directory

```bash
python shared_memory.py
```

## Expected output

1. Agent A stores tenant-scoped memory for `team-alpha`.
2. Agent B stores tenant-scoped memory for `team-beta`.
3. Each agent retrieves only its own tenant's facts.
4. Queries never reveal the other tenant's underlying content.

Look for lines similar to:

```text
Agent A sees payment gateway content: True
Agent B sees payment gateway content: False
Agent B sees Kubernetes content: True
Tenant isolation confirmed ...
```
