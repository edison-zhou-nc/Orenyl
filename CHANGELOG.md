# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and this project follows semantic versioning.

## [0.5.0] - Unreleased

### Added
- Explicit local stdio development mode for self-serve onboarding and demos.

### Changed
- Renamed the public PyPI distribution to `orenyl-mcp-server` to avoid conflict with an unrelated `lore-mcp` package.
- Clarified public launch messaging to distinguish local development from authenticated production deployment.
- Aligned the MCP contract and onboarding docs with the live runtime behavior.

## [0.4.0] - 2026-03-16

### Added
- Final release readiness, security, compliance, and documentation gates.
- CI-backed health and performance release checks.

### Changed
- Promoted package metadata from `0.4.0rc1` to `0.4.0`.
- Updated project metadata and repository URLs for public launch.

## [0.4.0rc1] - 2026-03-16

### Added
- Release decomposition gates for `src/orenyl/db.py` and `src/orenyl/server.py`.
- Release metadata, package version export, and repository URLs.
- Release, migration, integration, scaling, DR, and architecture documentation.

### Changed
- Split database persistence into repository mixins while keeping `from orenyl.db import Database` stable.
- Split MCP handler logic into `orenyl.handlers.*` modules while keeping `orenyl.server.handle_*` imports stable.
- Trimmed `src/orenyl/server.py` to runtime wiring, dispatch, transport, and entrypoints.

### Fixed
- Removed shadowed legacy database methods and dead legacy server handlers.
- Added regression tests for handler exports, decomposition completeness, and package export surfaces.

## [0.1.0] - 2026-03-14

### Added
- Beta governed-memory MCP server with event, fact, lineage, deletion, audit, consent, tenant, and DR support.
