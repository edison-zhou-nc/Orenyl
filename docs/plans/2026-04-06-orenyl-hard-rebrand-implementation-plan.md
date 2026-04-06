# Orenyl Hard Rebrand Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rename the project from `Lore` to `Orenyl` as a hard break across package namespace, distribution name, CLI, environment variables, docs, workflows, and examples.

**Architecture:** Make the rebrand land in one coherent sweep on an isolated branch. Start by writing failing contract tests for the new `orenyl` public surface, then rename the Python package and runtime interfaces, then update packaging, docs, workflows, scripts, and examples, and finally remove transition-only tests once the new brand is fully verified.

**Tech Stack:** Python 3.12, setuptools/pyproject packaging, pytest, ruff, mypy, GitHub Actions, Docker

---

### Task 1: Freeze the New Public Contract in Tests

**Files:**
- Modify: `tests/unit/test_release_metadata.py`
- Modify: `tests/unit/test_public_launch_docs.py`
- Modify: `tests/unit/test_packaging_install_smoke.py`
- Modify: `tests/unit/test_release_workflow.py`
- Test: `tests/unit/test_release_metadata.py`
- Test: `tests/unit/test_public_launch_docs.py`
- Test: `tests/unit/test_packaging_install_smoke.py`
- Test: `tests/unit/test_release_workflow.py`

**Step 1: Write the failing tests**

Add assertions for the new canonical surface:

```python
assert 'name = "orenyl-mcp-server"' in pyproject
assert 'orenyl-server = "orenyl.server:main"' in pyproject
assert 'python -m orenyl.server' in workflow
assert 'import orenyl, orenyl.server' in workflow
assert "pip install orenyl-mcp-server" in readme
assert "orenyl-server" in readme
importlib.import_module("orenyl")
importlib.import_module("orenyl.server")
```

Use targeted negative checks only where they protect the final contract, for example:

```python
assert 'name = "lore-mcp-server"' not in pyproject
```

Do not add a permanent broad "ban every use of lore in the repo" test. Those transition-only checks should be temporary and removed later.

**Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/unit/test_release_metadata.py tests/unit/test_public_launch_docs.py tests/unit/test_packaging_install_smoke.py tests/unit/test_release_workflow.py -q
```

Expected: FAIL because the repo still exposes `lore` names.

**Step 3: Commit the failing tests**

```bash
git add tests/unit/test_release_metadata.py tests/unit/test_public_launch_docs.py tests/unit/test_packaging_install_smoke.py tests/unit/test_release_workflow.py
git commit -m "test: freeze Orenyl public contract"
```

### Task 2: Rename the Python Package Namespace

**Files:**
- Rename: `src/lore` -> `src/orenyl`
- Modify: `pyproject.toml`
- Modify: `scripts/demo_v2.py`
- Modify: `scripts/lore_dr.py`
- Modify: `scripts/run_eval.py`
- Modify: `examples/meeting-memory/meeting_memory.py`
- Modify: `examples/personal-health-tracker/health_tracker.py`
- Modify: `examples/multi-agent-shared-memory/shared_memory.py`
- Modify: all `tests/**/*.py` files importing `lore`
- Test: `tests/unit/test_packaging_install_smoke.py`
- Test: `tests/unit/test_package_exports.py`

**Step 1: Rename the package directory**

Run:

```bash
git mv src/lore src/orenyl
```

**Step 2: Rewrite imports**

Replace imports like:

```python
from lore.db import Database
from lore import server
import lore.server as server_module
```

with:

```python
from orenyl.db import Database
from orenyl import server
import orenyl.server as server_module
```

Use:

```bash
rg -l "from lore|import lore|python -m lore\\.server" src tests scripts examples
```

and update every returned tracked file.

**Step 3: Update package metadata paths**

In `pyproject.toml`, update package-data and coverage/source paths:

```toml
[project.scripts]
orenyl-server = "orenyl.server:main"

[tool.setuptools.package-data]
orenyl = ["schema.sql", "py.typed"]

[tool.coverage.run]
source = ["src/orenyl"]
```

**Step 4: Run targeted smoke tests**

Run:

```bash
python -m pytest tests/unit/test_packaging_install_smoke.py tests/unit/test_package_exports.py -q
python -c "import orenyl, orenyl.server; print('ok')"
```

Expected: PASS and print `ok`.

**Step 5: Commit**

```bash
git add src/orenyl pyproject.toml scripts examples tests
git commit -m "refactor: rename Python package namespace to orenyl"
```

### Task 3: Rename Runtime Commands and Environment Variables

**Files:**
- Modify: `src/orenyl/env_vars.py`
- Modify: `src/orenyl/server.py`
- Modify: `src/orenyl/server_stdio.py`
- Modify: `README.md`
- Modify: `docs/quickstart.md`
- Modify: `docs/INTEGRATION.md`
- Modify: `docs/guides/openclaw.md`
- Modify: `docs/guides/claude-code.md`
- Modify: `tests/unit/test_readme_config_docs.py`
- Modify: `tests/integration/test_server_transport_modes.py`
- Modify: `tests/integration/test_server_misconfiguration.py`
- Modify: `tests/integration/test_server_authz_enforcement.py`

**Step 1: Rename environment variable constants**

Update every public env var from `LORE_*` to `ORENYL_*`.

Representative example:

```python
TRANSPORT = "ORENYL_TRANSPORT"
ALLOW_STDIO_DEV = "ORENYL_ALLOW_STDIO_DEV"
OIDC_AUDIENCE = "ORENYL_OIDC_AUDIENCE"
OIDC_ISSUER = "ORENYL_OIDC_ISSUER"
```

**Step 2: Rename command and module references**

Replace:

```text
lore-server
python -m lore.server
```

with:

```text
orenyl-server
python -m orenyl.server
```

**Step 3: Update runtime docs and config examples**

Change example snippets to:

```json
{
  "orenyl": {
    "command": "orenyl-server"
  }
}
```

and PowerShell examples to:

```powershell
$env:ORENYL_ALLOW_STDIO_DEV = "1"
$env:ORENYL_TRANSPORT = "stdio"
```

**Step 4: Run focused tests**

Run:

```bash
python -m pytest tests/unit/test_readme_config_docs.py tests/integration/test_server_transport_modes.py tests/integration/test_server_misconfiguration.py -q
```

Expected: PASS with only `ORENYL_*` and `orenyl-server` in the validated surfaces.

**Step 5: Commit**

```bash
git add src/orenyl README.md docs tests
git commit -m "refactor: rename runtime commands and env vars to orenyl"
```

### Task 4: Rename Distribution, Metadata, and GitHub Surfaces

**Files:**
- Modify: `pyproject.toml`
- Modify: `.github/workflows/ci.yml`
- Modify: `.github/workflows/release.yml`
- Modify: `Dockerfile`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `SECURITY.md`
- Modify: `CONTRIBUTING.md`
- Modify: `tests/unit/test_release_metadata.py`
- Modify: `tests/unit/test_release_workflow.py`

**Step 1: Update package metadata**

In `pyproject.toml`, replace:

```toml
name = "lore-mcp-server"
authors = [{ name = "Lore Maintainers" }]
Homepage = "https://github.com/edison-zhou-nc/Lore"
```

with:

```toml
name = "orenyl-mcp-server"
authors = [{ name = "Orenyl Maintainers" }]
Homepage = "https://github.com/edison-zhou-nc/orenyl"
```

Update `Repository`, `Issues`, and `Changelog` URLs the same way.

**Step 2: Update workflow names and artifact labels**

Rename workflow smoke commands and artifact labels such as:

```yaml
python -m mypy src/orenyl --config-file pyproject.toml
python -m pytest tests/unit tests/integration -q --cov=src/orenyl --cov-report=term-missing --cov-fail-under=80
python -c "import orenyl, orenyl.server"
name: orenyl-dist
```

**Step 3: Update Docker/runtime labels**

Representative replacements:

```dockerfile
adduser --disabled-password --gecos "" --uid 10001 orenyl
CMD ["python", "-m", "orenyl.server"]
```

**Step 4: Run metadata/workflow tests**

Run:

```bash
python -m pytest tests/unit/test_release_metadata.py tests/unit/test_release_workflow.py -q
python -m build
```

Expected: PASS and build artifacts named `orenyl_mcp_server-...`.

**Step 5: Commit**

```bash
git add pyproject.toml .github/workflows Dockerfile README.md CHANGELOG.md SECURITY.md CONTRIBUTING.md tests
git commit -m "chore: rename package metadata and release surfaces to Orenyl"
```

### Task 5: Update Examples, Scripts, and User Guides

**Files:**
- Modify: `examples/meeting-memory/README.md`
- Modify: `examples/personal-health-tracker/README.md`
- Modify: `examples/multi-agent-shared-memory/README.md`
- Modify: `examples/meeting-memory/meeting_memory.py`
- Modify: `examples/personal-health-tracker/health_tracker.py`
- Modify: `examples/multi-agent-shared-memory/shared_memory.py`
- Modify: `scripts/demo_v2.py`
- Modify: `scripts/lore_dr.py`
- Modify: `scripts/run_eval.py`
- Modify: `docs/guides/openclaw.md`
- Modify: `docs/guides/claude-code.md`
- Modify: `docs/quickstart.md`

**Step 1: Update install and invocation text**

Examples must show only:

```bash
pip install orenyl-mcp-server
orenyl-server
python -m orenyl.server
```

**Step 2: Update example import and error messages**

Representative replacement:

```python
raise SystemExit("Install Orenyl first with `python -m pip install -e .`.") from exc
```

**Step 3: Update guide configuration examples**

Use `orenyl` as the MCP server key in example JSON blocks:

```json
{
  "orenyl": {
    "args": ["-m", "orenyl.server"]
  }
}
```

**Step 4: Run focused tests or smoke scripts**

Run:

```bash
python -m pytest tests/unit/test_public_launch_docs.py -q
python scripts/demo_v2.py
```

If `scripts/demo_v2.py` is too heavyweight for local validation, replace it with a direct import smoke check and document why.

**Step 5: Commit**

```bash
git add examples scripts docs
git commit -m "docs: rename guides and examples to Orenyl"
```

### Task 6: Sweep Product Docs and Repo Narrative

**Files:**
- Modify: `README.md`
- Modify: `docs/DR.md`
- Modify: `docs/COMPLIANCE_READINESS.md`
- Modify: `docs/ADR.md`
- Modify: `docs/MCP_TOOL_CONTRACTS.md`
- Modify: `docs/INTEGRATION.md`
- Modify: `docs/MIGRATION.md`
- Modify: `docs/SECURITY_AUDIT.md`
- Modify: `docs/SCALING.md`
- Modify: `docs/RELEASE_PROCESS.md`
- Modify: `docs/benchmarks/v2-baseline.md`
- Modify: `LICENSE`

**Step 1: Replace public brand references**

Every product-facing sentence should refer to `Orenyl`, not `Lore`.

Representative edits:

```text
Lore is ready for self-serve local development...
```

becomes:

```text
Orenyl is ready for self-serve local development...
```

**Step 2: Update repo paths and screenshots**

Update badge/image references and clone instructions:

```text
https://github.com/edison-zhou-nc/orenyl
git clone https://github.com/edison-zhou-nc/orenyl.git
cd orenyl
```

Rename product-facing asset references if needed, for example `lore_social_preview.png` -> `orenyl_social_preview.png`.

**Step 3: Update legal/copyright strings**

Representative example:

```text
Copyright 2026 Orenyl Maintainers
```

**Step 4: Run docs-focused tests**

Run:

```bash
python -m pytest tests/unit/test_public_launch_docs.py tests/unit/test_readme_config_docs.py -q
```

Expected: PASS with docs showing only the `orenyl` public contract.

**Step 5: Commit**

```bash
git add README.md docs LICENSE tests
git commit -m "docs: rebrand repository narrative to Orenyl"
```

### Task 7: Remove Transition-Only Tests and Verify the Final Surface

**Files:**
- Modify: `tests/unit/test_release_metadata.py`
- Modify: `tests/unit/test_public_launch_docs.py`
- Modify: `tests/unit/test_release_workflow.py`
- Modify: `tests/unit/test_packaging_install_smoke.py`

**Step 1: Remove temporary transition-only assertions**

Delete any broad anti-`lore` checks that were useful during migration but are now too brittle.

Keep durable assertions like:

```python
assert 'name = "orenyl-mcp-server"' in pyproject
importlib.import_module("orenyl")
importlib.import_module("orenyl.server")
```

Remove migration-only rules like:

```python
assert "lore" not in some_large_file_blob
```

unless they protect an enduring public contract.

**Step 2: Run focused tests**

Run:

```bash
python -m pytest tests/unit/test_release_metadata.py tests/unit/test_public_launch_docs.py tests/unit/test_release_workflow.py tests/unit/test_packaging_install_smoke.py -q
```

Expected: PASS with the durable `Orenyl` contract intact.

**Step 3: Run full verification**

Run:

```bash
python -m ruff check . --select F,B
python -m mypy src/orenyl --config-file pyproject.toml
python -m pytest tests/unit tests/integration -q --cov=src/orenyl --cov-report=term-missing --cov-fail-under=80
python -m build
python -c "import orenyl, orenyl.server; print('ok')"
```

Expected:

- `ruff`: PASS
- `mypy`: PASS
- `pytest`: PASS
- `build`: PASS
- smoke import: prints `ok`

**Step 4: Update the git remote**

Run:

```bash
git remote set-url Lore https://github.com/edison-zhou-nc/orenyl.git
git remote -v
```

Expected: fetch and push URLs point to `.../orenyl.git`.

**Step 5: Commit**

```bash
git add .
git commit -m "feat: hard rebrand Lore to Orenyl"
```

### Task 8: Final Review and Handoff

**Files:**
- Modify: `docs/plans/2026-04-06-orenyl-hard-rebrand-design.md` only if implementation decisions changed
- Modify: `docs/plans/2026-04-06-orenyl-hard-rebrand-implementation-plan.md` only if implementation decisions changed materially

**Step 1: Summarize final breaking changes**

Document the final hard-break commands in the release notes or final handoff:

```text
pip install orenyl-mcp-server
orenyl-server
python -m orenyl.server
import orenyl
ORENYL_*
```

**Step 2: Capture the verification results**

Record the command outputs that matter:

- test count
- coverage
- build artifact names
- smoke import result

**Step 3: Sanity-check repo status**

Run:

```bash
git status --short --branch
```

Expected: clean working tree on `rebrand/orenyl-hardbreak`.

**Step 4: Commit any final plan/doc updates**

```bash
git add docs/plans
git commit -m "docs: finalize Orenyl rebrand handoff"
```

Only do this if the plan or design docs changed during execution.

**Step 5: Prepare for review**

Request code review, then use `@superpowers:finishing-a-development-branch` before merge or cleanup.

