# Architecture Decisions

## ADR 1: Preserve the `Database` import surface

The GA refactor keeps `from lore.db import Database` stable. Internal persistence moved into repository mixins to reduce file size and improve reviewability without forcing constructor churn across the codebase.

## ADR 2: Preserve `lore.server.handle_*` imports

Handler logic moved into `lore.handlers.*`, but `lore.server` still re-exports the established handler names. This keeps tests and integrators stable while allowing `server.py` to shrink.

## ADR 3: Use lazy dependency access for handlers

Handlers access runtime singletons through `lore.handlers._deps`. This is intentionally coupled to `lore.server` and favors import compatibility over fully standalone handlers.

## ADR 4: Treat decomposition as a gated invariant

The repo now has tests that enforce `db.py` and `server.py` size ceilings and verify the exported handler surface so structural regression is caught in CI.

