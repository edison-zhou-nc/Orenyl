# Release Checklist

## Ship posture

Use this checklist for every public beta / early production release. The goal is
to keep the release gate small, explicit, and repeatable.

## Preconditions

- Confirm the branch is ready to cut and the tree is clean. Start from a clean
  working tree.
- Bootstrap the release tools before the editable install:

```bash
python -m pip install bandit pip-audit pytest-cov build mypy
```

- Install the project in editable mode from the repo root:

```bash
python -m pip install --no-deps -e .
```

- Run the release verifier from the repo root after the bootstrap and editable
  install:

```bash
python scripts/verify_release.py
```

## Local verification

- Run the release verifier locally before tagging.
- Confirm the release posture still matches public beta / early production
  expectations.
- Check that the clean working tree requirement still holds after the final
  verification pass.

## CI / tagged-release verification

- Confirm the tag-triggered workflow enforces the tagged-release gate and only
  publishes on a green result.
- Confirm CI produces the same pass/fail signal you saw locally.
- Do not publish until the tagged release is green.

## Release artifacts to inspect

- Source distribution and wheel output.
- The generated release notes or changelog entry.
- Any smoke-test output tied to the built artifacts.
- The final release artifacts that will be published from CI.

## Rollback / hotfix path

- If a release check fails after tagging, stop the publish and roll back to the
  last known good tag.
- If a production issue slips through, cut a hotfix from the latest release tag
  and re-run the same gate before publishing.
- Keep the rollback path simple so it can be executed without guesswork.
