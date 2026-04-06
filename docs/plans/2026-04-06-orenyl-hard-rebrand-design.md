# Orenyl Hard Rebrand Design

**Date:** 2026-04-06

**Status:** Approved

**Decision:** Rebrand the project from `Lore` to `Orenyl` as a hard break with no compatibility shim.

## Goal

Replace the product, package, runtime, and repository identity from `Lore` to `Orenyl` across the codebase so the project launches under a single consistent brand.

## Why

- `Lore` is too crowded and adjacent to existing memory/AI brands.
- The project is still pre-adoption, so a hard break is cheaper now than later.
- Mixed branding would create confusion across install docs, Python imports, CLI usage, and launch materials.

## Rebrand Scope

The rebrand applies to all public and internal surfaces.

### Public surfaces to rename

- Project/product name: `Lore` -> `Orenyl`
- Distribution name: `lore-mcp-server` -> `orenyl-mcp-server`
- CLI: `lore-server` -> `orenyl-server`
- Module entrypoint: `python -m lore.server` -> `python -m orenyl.server`
- GitHub URLs: `.../Lore` -> `.../orenyl`
- Public docs, badges, screenshots, examples, and guides

### Internal/runtime surfaces to rename

- Python package namespace: `lore` -> `orenyl`
- Source directory: `src/lore/` -> `src/orenyl/`
- Environment variables: `LORE_*` -> `ORENYL_*`
- Workflow commands, build paths, coverage paths, and smoke tests
- Docker/runtime labels and other product-facing strings

## Intentional Breaking Changes

The following old surfaces will stop working:

- `import lore`
- `python -m lore.server`
- `lore-server`
- every `LORE_*` environment variable
- `pip install lore-mcp-server`

The new canonical surfaces are:

- `import orenyl`
- `python -m orenyl.server`
- `orenyl-server`
- `ORENYL_*`
- `pip install orenyl-mcp-server`

## Compatibility Policy

No compatibility bridge will be shipped.

- No alias package
- No deprecated CLI alias
- No environment variable fallback
- No `lore` import shim

This is acceptable because the project is still pre-adoption and the user explicitly chose a hard break.

## Execution Strategy

The rebrand should land in one coordinated sweep inside an isolated worktree.

### Phase 1: Core package/runtime rename

- rename `src/lore` to `src/orenyl`
- update imports across source, tests, scripts, and examples
- rename CLI entrypoints and module execution paths
- rename environment variables and runtime config references

### Phase 2: Packaging and metadata rename

- rename the distribution to `orenyl-mcp-server`
- update `pyproject.toml` metadata, package-data config, coverage config, and URLs
- update release workflow artifact names and smoke commands

### Phase 3: Docs/examples/repo rename

- update README, quickstart, guides, release docs, security/compliance docs, and plans where appropriate
- update example scripts and README instructions
- update badges, social-preview references, and GitHub links

### Phase 4: Verification and cleanup

- add temporary regression checks as needed to force the rebrand through the codebase
- verify lint, typing, tests, build, smoke import, and CLI using only `orenyl` names
- remove or relax transition-only tests once the successful `Orenyl` surface is verified

## Test Policy

During implementation, temporary regression tests are allowed to catch leftover `lore` branding in the most important public surfaces.

After the rebrand is complete:

- keep functional tests that validate the new `orenyl` package, import path, CLI, and docs
- remove broad transition-only tests whose only purpose was to ban the old brand everywhere
- keep only durable assertions that protect the new public contract

## Risks

### Mechanical rename risk

The codebase contains many import sites, docs references, workflow commands, and environment-variable mentions. A partial rename would leave the repo in a mixed-brand state.

### Runtime config risk

Renaming `LORE_*` to `ORENYL_*` is a true config break. Docs, examples, tests, and integration guides must all move together.

### Packaging risk

The package rename must stay consistent with the current package-identity fix so we do not regress from `lore-mcp-server` back to the conflicting historical name.

## Non-Goals

- no backward compatibility for old names
- no staged multi-release migration
- no partial public-only rename
- no marketing copy rewrite beyond what is necessary to keep branding consistent

## Approved Outcome

The repository should end this work with one coherent identity:

- package namespace: `orenyl`
- install command: `pip install orenyl-mcp-server`
- CLI: `orenyl-server`
- repo/product name: `Orenyl`

