# GitHub Announcement

## Title

Orenyl: governed memory for MCP agents

## Body

Agent memory is useful, but unmanaged memory is risky.

Orenyl is a governed memory MCP server for AI agents. It stores memory you can trace, audit, and actually delete.

The core proof is simple:

1. store a sensitive event
2. retrieve derived context
3. inspect the audit trace
4. delete the source event
5. verify the deleted content does not resurface

That is the part we care about most:

Vector stores remember. Orenyl governs.

If you want to try it:
- Quickstart: [docs/quickstart.md](../quickstart.md)
- Demo flow: [scripts/demo_health_marketing.py](../../scripts/demo_health_marketing.py)

Orenyl is in public beta / early production. It is built for technical builders who need governed memory for sensitive or high-trust workflows.
