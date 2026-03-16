# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and this project follows semantic versioning.

## [1.0.0] - 2026-03-16

### Added
- Final GA readiness, security, compliance, release, and documentation gates.
- CI-backed health and performance release checks.

### Changed
- Promoted package metadata from `1.0.0rc1` to `1.0.0`.
- Updated project classifiers to reflect production/stable release status.

## [1.0.0rc1] - 2026-03-16

### Added
- GA decomposition gates for `src/lore/db.py` and `src/lore/server.py`.
- Release metadata, package version export, and repository URLs.
- Release, migration, integration, scaling, DR, and architecture documentation.

### Changed
- Split database persistence into repository mixins while keeping `from lore.db import Database` stable.
- Split MCP handler logic into `lore.handlers.*` modules while keeping `lore.server.handle_*` imports stable.
- Trimmed `src/lore/server.py` to runtime wiring, dispatch, transport, and entrypoints.

### Fixed
- Removed shadowed legacy database methods and dead legacy server handlers.
- Added regression tests for handler exports, decomposition completeness, and package export surfaces.

## [0.1.0] - 2026-03-14

### Added
- Beta governed-memory MCP server with event, fact, lineage, deletion, audit, consent, tenant, and DR support.
