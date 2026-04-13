# Reddit Post For r/LocalLLaMA

## Title

Built a governed memory layer for MCP agents that can prove deletion and non-resurfacing

## Body

I built Orenyl because I wanted a memory layer for agents that does more than store vectors or notes.

The main proof flow is:
- store a sensitive memory event
- retrieve a derived fact
- trace that fact back to source
- delete the source event
- verify the deleted content does not resurface

That is the product:

Vector stores remember. Orenyl governs.

I think this is most relevant for:
- MCP agents
- internal copilots
- high-trust workflows where memory needs auditability

It is not a hosted product and I am not claiming enterprise certification.
This is a public beta / early production open-source release for builders.

If people here are working on local or self-hosted agent stacks and care about governed memory, I'd love feedback on whether this is the right abstraction.
