# Release Process

For the exact pre-tag checklist, see [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md).
Use it for every public beta / early-production release.

## Release candidate

1. Bump package metadata to the next RC tag.
2. Run the focused launch-readiness regression set.
3. Run the full unit and integration suite with coverage.
4. Run Ruff, mypy, package build, and built-wheel smoke import.
5. Publish only after the release workflow reruns the same verification on the tag.

## Public launch release

1. Confirm launch docs are current and product claims match the shipped onboarding path.
2. Verify local development mode and authenticated production mode are both documented correctly.
3. Ensure the release workflow will rerun:
   - `python -m ruff check . --select F,B`
   - `python -m mypy src/orenyl --config-file pyproject.toml`
   - `python -m pytest tests/unit tests/integration -q --cov=src/orenyl --cov-report=term-missing --cov-fail-under=80`
   - `python -m build`
   - built-wheel smoke import in a clean virtual environment
4. Tag the release only after the branch is green locally and in CI.
5. Publish artifacts from the gated release workflow.

## Current release state

Orenyl is a public Beta release on PyPI. The project is ready for self-serve local
development, evaluation, and early production deployments with authenticated
`streamable-http` transport. External security certification, penetration testing,
and enterprise operator packaging are pending future work.

## Hotfix flow

1. Branch from the latest release tag.
2. Add a changelog entry for the fix.
3. Run the smallest targeted regression plus Ruff, mypy, build, and smoke import checks that cover the touched area.
4. Publish a patch release only after the release workflow reruns those checks on the tag.
