# Context Pack Specification v0.1

## What is a Context Pack?

A Context Pack is a bounded, agent-readable JSON document containing everything an AI agent needs to know about a user's current state — and nothing it shouldn't.

Unlike raw conversation history or append-only memory stores, a Context Pack contains only **currently valid, derived facts** with full **provenance traces** explaining why each fact is present and what evidence supports it.

## Design Principles

1. **Bounded**: A context pack has a fixed maximum size. Agents receive what they need, not everything that was ever stored.
2. **Traced**: Every fact includes provenance — which events it was derived from and which rule produced it.
3. **Time-valid**: Facts carry validity windows. Expired facts are excluded automatically.
4. **Governed**: Facts that depend on deleted events are invalidated and re-derived. Deleted information cannot resurface.
5. **Deterministic**: The same set of active events always produces the same context pack. AI is a consumer of context packs, not the author.

## JSON Schema

```json
{
  "schema_version": "0.1",
  "generated_at": "2026-03-02T12:34:56Z",
  "subject": {
    "id": "user:demo"
  },
  "items": [
    {
      "id": "fact:active_medications:v3",
      "type": "fact",
      "key": "active_medications",
      "value": ["metformin"],
      "validity": {
        "from": "2026-02-01T00:00:00Z",
        "to": null
      },
      "provenance": {
        "derived_from": ["event:med_started:abc123"],
        "rule": "MedicationActiveRule@v1",
        "version": 3
      }
    }
  ],
  "trace": {
    "query": "What meds am I on?",
    "included": [
      {
        "item_id": "fact:active_medications:v3",
        "why": ["key_match:med", "rule_output:MedicationActiveRule"],
        "lineage": ["event:med_started:abc123"],
        "lineage_available": true
      }
    ]
  }
}
```

## Field Reference

### Top-level

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | string | yes | Spec version (currently "0.1") |
| `generated_at` | string (ISO 8601) | yes | When this pack was generated |
| `subject` | object | yes | Who this context pack describes |
| `items` | array | yes | Currently valid facts |
| `trace` | object | yes | Why each item was included |

### Item (Fact)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Unique fact ID (format: `fact:<key>:v<version>`) |
| `type` | string | yes | Always "fact" in v0.1 |
| `key` | string | yes | Fact category (e.g. "active_medications") |
| `value` | any | yes | The fact's current value |
| `validity.from` | string (ISO 8601) | yes | When this fact became valid |
| `validity.to` | string or null | yes | When this fact expires (null = currently valid) |
| `provenance.derived_from` | array of strings | yes | Event IDs this fact was derived from |
| `provenance.rule` | string | yes | Which derivation rule produced this fact |
| `provenance.version` | integer | yes | Fact version number |

### Trace Entry

| Field | Type | Description |
|-------|------|-------------|
| `item_id` | string | Which fact this trace entry explains |
| `why` | array of strings | Reasons this fact was included |
| `lineage` | array of strings | Upstream event/fact IDs |
| `lineage_available` | boolean | Whether full lineage can be queried via audit_trace |

## How Agents Should Consume Context Packs

1. **Read `items` for current state.** Each item represents a currently valid fact about the user.
2. **Cite provenance in responses.** When referencing a fact, agents should be able to point to the `item_id` and `provenance` fields.
3. **Never cache context packs across sessions.** Always request a fresh pack — facts may have been invalidated since last retrieval.
4. **Respect `validity.to`.** If a fact has expired, don't use it even if it's in the pack (defensive coding).
5. **Use `trace` for explainability.** If a user asks "why did you say that?", the trace provides the answer.

## Deletion Guarantees

When an event is deleted via `delete_and_recompute`:

- All facts derived from that event are invalidated
- New fact versions are derived from remaining active events
- The deleted event's ID will never appear in any future context pack's `provenance.derived_from`
- A `DeleteProof` object documents exactly what was tombstoned, invalidated, and re-derived

This is the core governance guarantee: **deleted information cannot resurface.**
