# Lore with OpenClaw

Add Lore as an MCP server in OpenClaw to give your AI agent persistent, production-minded governed memory.

## Prerequisites

- [OpenClaw](https://openclaw.ai) installed and running
- Python 3.12+ with `lore-mcp-server` installed: `pip install lore-mcp-server`

## Setup

Add Lore as an MCP server in OpenClaw's configuration:

```json
{
  "mcpServers": {
    "lore": {
      "command": "python",
      "args": ["-m", "lore.server"],
      "env": {
        "LORE_TRANSPORT": "stdio",
        "LORE_ALLOW_STDIO_DEV": "1",
        "LORE_DB_PATH": "./openclaw_memory.db"
      }
    }
  }
}
```

`LORE_ALLOW_STDIO_DEV=1` disables Lore's production guard for stdio transport, so keep that setting for local development only.

Once configured, OpenClaw can use all 14 Lore MCP tools for persistent memory with governed deletion and audit guarantees.

## What OpenClaw Gets

| Capability | Tool | Description |
|-----------|------|-------------|
| **Remember** | `store_event` | Store observations, notes, decisions with domain tags |
| **Recall** | `retrieve_context_pack` | Get relevant facts ranked by query similarity |
| **Forget** | `delete_and_recompute` | Delete with cascade verification proof |
| **Trace** | `audit_trace` | See exactly where a fact came from |
| **Comply** | `erase_subject_data` | GDPR Article 17 erasure by subject |
| **Export** | `export_subject_data` | GDPR Article 20 data portability |

## Why Lore + OpenClaw

OpenClaw is an agent runtime that executes tasks. Lore is a governed memory layer that stores what happened with compliance guarantees.

- OpenClaw decides what to do and when
- Lore remembers what happened, with provable deletion

When you delete data from Lore, cascade invalidation ensures downstream facts derived from that data are also removed. This is different from simple key-value memory where deletion leaves derived information orphaned.

## Configuration

See the full [configuration reference](../../README.md#configuration) for all environment variables.

For production use with authentication, see [Integration Guide](../INTEGRATION.md).
