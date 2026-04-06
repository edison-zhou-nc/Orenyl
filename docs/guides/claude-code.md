# Lore with Claude Code

Add Lore as an MCP server in Claude Code to give Claude persistent, production-minded governed memory during local development.

## Setup

Add to your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "lore": {
      "command": "orenyl-server",
      "env": {
        "LORE_TRANSPORT": "stdio",
        "LORE_ALLOW_STDIO_DEV": "1",
        "LORE_DB_PATH": "./lore_memory.db"
      }
    }
  }
}
```

## Verify

Start Claude Code in your project directory. You should see `lore` listed as an available MCP server. Claude can now use all 14 Lore tools:

This stdio setup is for local development only. Production deployment mode should use authenticated `streamable-http`.

- `store_event` - remember something
- `retrieve_context_pack` - recall relevant memory
- `delete_and_recompute` - forget with verification
- `audit_trace` - trace where a fact came from

## Example Interaction

```text
You: Remember that I'm allergic to penicillin
Claude: [calls store_event with domains=["health"], sensitivity="high"]

You: What do you know about my health?
Claude: [calls retrieve_context_pack with domain="health"]

You: Forget everything about my allergies
Claude: [calls delete_and_recompute, returns deletion proof]
```

## Configuration

See the full [configuration reference](../../README.md#configuration) for all environment variables.

For production deployments with authentication, see [Integration Guide](../INTEGRATION.md).
