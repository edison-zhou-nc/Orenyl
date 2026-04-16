# Orenyl with OpenClaw

Orenyl gives your AI agent three immediate memory moves: remember new context, recall relevant facts, and forget a source memory while inspecting the deletion proof.

## Prerequisites

- [OpenClaw](https://openclaw.ai) installed and running
- Python 3.12+ with `orenyl-mcp-server` installed: `pip install orenyl-mcp-server`

## Setup

Add Orenyl as an MCP server in OpenClaw's configuration:

```json
{
  "mcpServers": {
    "orenyl": {
      "command": "orenyl-server",
      "env": {
        "ORENYL_TRANSPORT": "stdio",
        "ORENYL_ALLOW_STDIO_DEV": "1",
        "ORENYL_DB_PATH": "./openclaw_memory.db"
      }
    }
  }
}
```

`ORENYL_ALLOW_STDIO_DEV=1` disables Orenyl's production guard for stdio transport, so keep that setting for local development only.

Once configured, OpenClaw can use all 14 Orenyl MCP tools for persistent memory with governed deletion and audit guarantees.

## What OpenClaw Gets

| Capability | Tool | Description |
|-----------|------|-------------|
| **Remember** | `store_event` | Store observations, notes, decisions with domain tags |
| **Recall** | `retrieve_context_pack` | Get relevant facts ranked by query similarity |
| **Forget** | `delete_and_recompute` | Delete with cascade verification proof |
| **Trace** | `audit_trace` | See exactly where a fact came from |
| **Comply** | `erase_subject_data` | GDPR Article 17 erasure by subject |
| **Export** | `export_subject_data` | GDPR Article 20 data portability |

## Why Orenyl + OpenClaw

OpenClaw is an agent runtime that executes tasks. Orenyl is a governed memory layer that stores what happened with compliance guarantees.

- OpenClaw decides what to do and when
- Orenyl remembers what happened, with provable deletion

When you delete data from Orenyl, cascade invalidation ensures downstream facts derived from that data are also removed. This is different from simple key-value memory where deletion leaves derived information orphaned.

## Configuration

See the full [configuration reference](../../README.md#configuration) for all environment variables.

For production use with authentication, see [Integration Guide](../INTEGRATION.md).
