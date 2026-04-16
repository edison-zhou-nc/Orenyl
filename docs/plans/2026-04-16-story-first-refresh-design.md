# Story-First Refresh Design

## Context

Orenyl already has the product substance for a strong first impression:

- a proof-first health demo in `scripts/demo_health_marketing.py`
- README screenshots near the top of the repo
- `remember / recall / forget` teaching in the Claude Code and OpenClaw guides
- honest early-production positioning across the public docs

The gap is narrative clarity. The top-level copy still leads with implementation language such as "production-minded governed memory MCP server" instead of the buyer fear that makes the product legible: an agent that remembers data it was supposed to forget.

## Chosen Direction

Use a focused story-first refresh for the current launch surfaces. Do not add a REST API, a new product surface, or a comparison page in this pass. Keep the product and transport strategy intact. Tighten the public story so evaluators understand the risk, the promise, and the proof in under two minutes.

## Goals

- Make the README understandable in 10 seconds.
- Center the proof story: store, derive, delete, verify non-resurfacing.
- Align GitHub, PyPI, quickstart, FAQ, and client guides to the same narrative.
- Teach first-contact users with `remember`, `recall`, and `forget` before deeper tool names.
- Preserve current factual claims about beta status and production scope.

## Non-Goals

- No REST API or new transport work.
- No rename.
- No hosted/cloud product work.
- No comparison matrix or long-form thought-leadership content in this pass.
- No changes to the 14-tool contract or MCP strategy.

## Narrative Architecture

### 1. Hero problem

Lead with the risk, not the mechanism.

Primary hook:

`Your AI agent remembers everything. Can you prove it forgot?`

### 2. Product answer

State the plain-language category immediately after the hook.

Core answer:

`Orenyl is agent memory with deletion guarantees.`

### 3. Proof claim

Make the differentiator concrete before explaining implementation details.

Core claim:

`When data is removed, every derived insight is traced, invalidated, and recomputed so deleted information does not resurface.`

### 4. Credibility layer

Only after the risk and promise are clear should the copy mention:

- lineage
- auditable memory operations
- GDPR-oriented design
- MCP-native integration
- early production / public beta scope

### 5. Onboarding language

Public docs should teach the user mental model first:

- remember
- recall
- forget

Then map those concepts to `store_event`, `retrieve_context_pack`, and `delete_and_recompute`.

## Deliverables

### Core deliverables

- `README.md`
  - rewrite hero copy
  - shorten the top explanation
  - move the proof story to the forefront
  - keep the demo as the main evidence
- `pyproject.toml`
  - replace the package description with plain-language positioning aligned to the README
- `docs/quickstart.md`
  - lead with the proof flow before the MCP explanation
- `docs/launch-faq.md`
  - sharpen answers around naive deletion, proof, and generic memory alternatives
- `docs/guides/claude-code.md`
  - make the remember/recall/forget flow feel like the first value story
- `docs/guides/openclaw.md`
  - keep the integration details but strengthen the proof-first framing

### Supporting deliverable

- `docs/positioning.md`
  - source-of-truth messaging doc for README, PyPI, launch posts, and outreach

## Guardrails

- Do not claim Orenyl is the only product with deletion features.
- Do not imply competitors cannot delete data.
- Do not claim certification, GA, or enterprise completeness.
- Do not remove the existing MCP explanation entirely; move it below the value story.
- Do not replace precise technical language with vague marketing language after the hook.
- Do not expand scope into new APIs, new protocols, or new product features.

## Success Criteria

- The first 15 lines of `README.md` communicate the problem, product, and proof clearly.
- PyPI metadata reflects the new story instead of the old jargon-heavy phrasing.
- `docs/quickstart.md` gets evaluators to the proof flow faster.
- `docs/launch-faq.md` answers the "why not just delete the row?" objection directly.
- Client guides feel simpler on first read without losing operational honesty.
- Existing release-positioning guardrails still pass after the rewrite.

## Verification Strategy

Use the existing doc and release-positioning tests as the main safety net:

- `tests/unit/test_public_launch_docs.py`
- `tests/unit/test_release_positioning.py`
- `tests/unit/test_release_metadata.py`
- `tests/unit/test_readme_config_docs.py`

Add or adjust targeted string assertions only where needed to protect the new story without making the docs too brittle.

## Follow-On Work

Once this refresh lands and real evaluators respond to it, the next likely moves are:

1. turn the health demo into an even more explicit "naive deletion fails" proof asset
2. add a comparison page after the story stabilizes
3. revisit a thin REST layer only if evaluators repeatedly ask for it
