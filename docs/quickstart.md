# Quickstart: Lore in 5 Minutes

Get Lore running locally in documented self-serve development mode, then exercise the MCP tool interface directly.

## Install

```bash
pip install lore-mcp-server
```

Or from source:

```bash
git clone https://github.com/edison-zhou-nc/Lore.git
cd Lore
python -m pip install -e .
```

## Start Lore in local dev mode

```powershell
$env:LORE_TRANSPORT = "stdio"
$env:LORE_ALLOW_STDIO_DEV = "1"
lore-server
```

This mode uses Lore's explicit local-dev auth bypass, so you do not need `_auth_token` or OIDC setup.
It is for development only.

## Configure your MCP client

```json
{
  "mcpServers": {
    "lore": {
      "command": "lore-server",
      "env": {
        "LORE_TRANSPORT": "stdio",
        "LORE_ALLOW_STDIO_DEV": "1",
        "LORE_DB_PATH": "./lore_memory.db"
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

## What just happened?

1. Lore stored an immutable event.
2. Lore derived deterministic facts from active events.
3. Retrieval returned bounded context with lineage.
4. Deletion invalidated downstream facts and verified they do not resurface.

This is Lore's core guarantee: if upstream data is deleted, downstream derivations must not resurface.

## Next steps

- [INTEGRATION.md](INTEGRATION.md)
- [guides/claude-code.md](guides/claude-code.md)
- [guides/openclaw.md](guides/openclaw.md)
- [MCP_TOOL_CONTRACTS.md](MCP_TOOL_CONTRACTS.md)
