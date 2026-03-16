# Release Process

## Release candidate

1. Bump package metadata to `1.0.0rc1`.
2. Run targeted packaging, decomposition, docs, health, and perf gates.
3. Build wheel and sdist artifacts.
4. Smoke import the built package.

## GA release

1. Confirm all release docs are present and current.
2. Run the full unit and integration suite.
3. Run the GA gate tests, lint, format, and build commands.
4. Bump from `1.0.0rc1` to `1.0.0`.
5. Tag and publish artifacts.

## Hotfix flow

1. Branch from the latest release tag.
2. Add a changelog entry for the fix.
3. Run the smallest targeted regression plus packaging checks.
4. Publish a patch release after validation.
