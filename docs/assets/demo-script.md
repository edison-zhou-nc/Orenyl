# Orenyl Health Demo Capture Guide

## Goal

Capture a simple before/after proof pair that makes the product obvious at a glance:

1. Before: `Stored memory` and `Derived fact now`
2. After: `Delete request`, `Verification`, and `Facts after deletion`

## Setup

- Use a large terminal font
- Keep the terminal width wide enough that `Stored memory`, `Derived fact now`, and `Facts after deletion` stay readable
- Run from the repo root of the checkout or worktree where you are preparing launch assets
- Prefer a clean terminal with no other scrolling noise

## Command

```bash
python scripts/demo_health_marketing.py
```

## Capture Targets

- `orenyl_health_before.png`
  Capture the `Stored memory` section and the `Derived fact now` section together. This is the hero proof for the setup story.
- `orenyl_health_after.png`
  Capture the `Delete request`, `Verification`, and `Facts after deletion` sections together, including the final `RESULT: deleted health content does not resurface.` line. This is the hero proof for the deletion story.
- `orenyl_health_audit_trace.png` optional
  Capture the `Audit trace` section only if you want a supporting credibility image. This is supporting evidence, not the main launch image.

## Where To Use Them

- README: show `orenyl_health_before.png` and `orenyl_health_after.png` together near the top.
- Launch posts: lead with `orenyl_health_after.png` when space is tight, because deletion proof is the differentiator.
- README and posts: use `orenyl_health_audit_trace.png` only as a secondary trust signal.

## Copy Hooks

- `Governed memory for MCP agents`
- `Store agent memory you can trace, audit, and actually delete.`
- `Vector stores remember. Orenyl governs.`

## Notes

- This is a product-proof capture, not a benchmark run.
- Keep the health example framed as sensitive-memory proof, not medical certification claims.
- If a line is too noisy for capture, trim the script output rather than explaining around it.
