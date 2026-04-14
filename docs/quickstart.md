# Quickstart: Orenyl in 5 Minutes

Get Orenyl running locally in documented self-serve development mode, then exercise the MCP tool interface directly.

## 30-Second Primer

### What is MCP?

MCP stands for Model Context Protocol. It is the standard way an AI client discovers tools from a server and calls them over stdio or HTTP.

### Why should I care?

With Orenyl over MCP, a client such as Claude Code can remember events, retrieve relevant context, verify deletions, and inspect lineage without a custom integration layer.

## Install

As of April 14, 2026, Orenyl `0.5.0` is not yet published on PyPI. Use a source checkout for now:

```bash
git clone https://github.com/edison-zhou-nc/Orenyl.git
cd Orenyl
python -m pip install -e .
```

Once the public package is live, the install becomes:

```bash
pip install orenyl-mcp-server
```

## Start Orenyl in local dev mode

```powershell
$env:ORENYL_TRANSPORT = "stdio"
$env:ORENYL_ALLOW_STDIO_DEV = "1"
orenyl-server
```

This mode uses Orenyl's explicit local-dev auth bypass, so you do not need `_auth_token` or OIDC setup.
It is for development only.

## Configure your MCP client

```json
{
  "mcpServers": {
    "orenyl": {
      "command": "orenyl-server",
      "env": {
        "ORENYL_TRANSPORT": "stdio",
        "ORENYL_ALLOW_STDIO_DEV": "1",
        "ORENYL_DB_PATH": "./orenyl_memory.db"
      }
    }
  }
}
```

## Try the core tool flow

### 1. Store an event

```json
{
  "name": "store_event",
  "arguments": {
    "domains": ["health"],
    "type": "med_started",
    "payload": {"name": "metformin"},
    "sensitivity": "medium"
  }
}
```

Expected result: a response containing `stored: true` and an `event_id`.

### 2. Retrieve a context pack

```json
{
  "name": "retrieve_context_pack",
  "arguments": {
    "domain": "health",
    "query": "medication",
    "limit": 10
  }
}
```

Expected result: facts plus lineage-aware retrieval metadata.

### 3. Delete with verification

```json
{
  "name": "delete_and_recompute",
  "arguments": {
    "target_id": "event:replace-with-your-event-id",
    "target_type": "event",
    "reason": "user_request",
    "mode": "soft"
  }
}
```

Expected result: a deletion proof whose checks include `deletion_verified: true`.

### 4. Inspect lineage

```json
{
  "name": "audit_trace",
  "arguments": {
    "item_id": "event:replace-with-your-event-id",
    "include_source_events": true
  }
}
```

Expected result: a full lineage trace showing upstream and downstream relationships.

## Production note

Production deployment uses `streamable-http` and authenticated tool calls. When auth is enabled, pass `auth_token` on FastMCP-registered tools or `_auth_token` in raw tool arguments. This path replaces the development-only stdio flow. See [INTEGRATION.md](INTEGRATION.md) for the exact contract.

If you want the same flow exercised by an automated end-to-end client, run `python -m pytest tests/integration/test_stdio_mcp_client_smoke.py -q` from the repo root.

## What just happened?

1. Orenyl stored an immutable event.
2. Orenyl derived deterministic facts from active events.
3. Retrieval returned bounded context with lineage.
4. Deletion invalidated downstream facts and verified they do not resurface.

This is Orenyl's core guarantee: if upstream data is deleted, downstream derivations must not resurface.

## Next steps

- [INTEGRATION.md](INTEGRATION.md)
- [guides/claude-code.md](guides/claude-code.md)
- [guides/openclaw.md](guides/openclaw.md)
- [../examples/README.md](../examples/README.md)
- [MCP_TOOL_CONTRACTS.md](MCP_TOOL_CONTRACTS.md)
