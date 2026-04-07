# Contributing

Please review [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before participating and
use [SECURITY.md](SECURITY.md) for private vulnerability reporting.

## Development Setup

1. Install Python 3.12+
2. Install dependencies:

```bash
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python -m pip install -e .
```

## Test Requirements

Run before opening a PR:

```bash
python -m pytest -q
```

## Validation Commands

Run the launch-readiness checks before opening a PR:

```bash
python -m ruff check . --select F,B
python -m mypy src/orenyl --config-file pyproject.toml
python -m build
```

## Code Style

- Ruff + Black configuration lives in `pyproject.toml`.
- Keep changes focused and include tests for behavioral changes.

## Pull Requests

- Explain the problem, approach, and validation.
- Include any migration/config impact.
- Keep PRs small and reviewable.

## Community and Security

- Follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) in issues, discussions, and PRs.
- Report sensitive security findings privately per [SECURITY.md](SECURITY.md).

## Disaster Recovery Notes

- `restore_snapshot` uses SQLite backup into the active DB connection.
- After restore, restart the server process to ensure all long-lived runtime objects
  and caches are fully consistent with restored state.
