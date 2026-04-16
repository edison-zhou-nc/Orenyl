# Orenyl with Claude Code

Orenyl gives Claude three immediate memory moves during local development: remember new user context, recall relevant facts, and forget a source memory while showing the deletion proof.

The first smoke-test sequence proves the loop end to end: store a memory, ask for it back, then delete it and confirm the derived context no longer resurfaces.

Orenyl `0.5.0` is published on PyPI. For the shortest setup path, install `pip install orenyl-mcp-server`; use an editable source checkout only if you are actively developing Orenyl itself.

## Setup

Add to your project's `.mcp.json`:

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

## Verify

Start Claude Code in your project directory. You should see `orenyl` listed as an available MCP server. Claude can now use all 14 Orenyl tools:

This stdio setup is for local development only. Production deployment mode should use authenticated `streamable-http`.

- `store_event` - remember something
- `retrieve_context_pack` - recall relevant memory
- `delete_and_recompute` - forget with verification
- `audit_trace` - trace where a fact came from

## Smoke test prompts

Use this short sequence in Claude Code after the server appears:

```text
Remember that I started metformin.
What do you remember about my health?
Forget the metformin memory and show me the deletion proof.
```

If you want a scripted end-to-end check outside Claude Code, run `python -m pytest tests/integration/test_stdio_mcp_client_smoke.py -q` from the repo root.

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
