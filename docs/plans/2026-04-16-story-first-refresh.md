# Story-First Refresh Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refresh Orenyl's public story so a new evaluator understands deletion-proof agent memory in 10 seconds and reaches the proof flow in under two minutes.

**Architecture:** Keep the product surface unchanged and update only the public messaging stack. The work centers on aligning README, PyPI metadata, quickstart, FAQ, and client guides to the same risk -> promise -> proof story while preserving current beta-honest language and MCP integration details. Lightweight pytest assertions should guard the new story against future drift.

**Tech Stack:** Markdown docs, TOML package metadata, pytest doc-positioning tests

---

### Task 1: Establish the messaging source and hero story

**Files:**
- Create: `docs/positioning.md`
- Create: `tests/unit/test_story_first_positioning.py`
- Modify: `README.md`
- Modify: `pyproject.toml`

**Step 1: Write the failing test**

Add a focused test file that checks for the new story without overfitting every sentence.

```python
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_story_first_surfaces_lead_with_problem_and_proof() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8").lower()
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8").lower()

    assert "can you prove it forgot" in readme
    assert "agent memory with deletion guarantees" in readme
    assert "agent memory with deletion guarantees" in pyproject
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_story_first_positioning.py -q`
Expected: FAIL because the new story is not present yet.

**Step 3: Write minimal implementation**

- Create `docs/positioning.md` as the source of truth for:
  - hero hook
  - product answer
  - proof claim
  - approved supporting phrases
  - phrases to avoid
- Rewrite the first screen of `README.md` to follow this order:

```md
Your AI agent remembers everything. Can you prove it forgot?

Orenyl is agent memory with deletion guarantees.

When data is removed, every derived insight is traced, invalidated, and recomputed so deleted information does not resurface.
```

- Update `pyproject.toml` so `[project].description` matches the plain-language story rather than the current jargon-heavy phrasing.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_story_first_positioning.py tests/unit/test_release_positioning.py tests/unit/test_release_metadata.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add docs/positioning.md tests/unit/test_story_first_positioning.py README.md pyproject.toml
git commit -m "docs: refresh top-level positioning story"
```

### Task 2: Reframe the quickstart and FAQ around proof

**Files:**
- Modify: `docs/quickstart.md`
- Modify: `docs/launch-faq.md`
- Modify: `tests/unit/test_public_launch_docs.py`

**Step 1: Write the failing test**

Add assertions that protect the faster proof-first flow.

```python
def test_quickstart_and_faq_explain_proof_first_value() -> None:
    quickstart = (REPO_ROOT / "docs" / "quickstart.md").read_text(encoding="utf-8").lower()
    faq = (REPO_ROOT / "docs" / "launch-faq.md").read_text(encoding="utf-8").lower()

    assert "proof" in quickstart
    assert "naive deletion" in faq or "delete the row" in faq
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_public_launch_docs.py -q`
Expected: FAIL on the new assertion.

**Step 3: Write minimal implementation**

- Move the quickstart opening toward:
  - what goes wrong with normal memory deletion
  - what Orenyl proves
  - the proof flow the evaluator should try first
- Keep the MCP explainer, but move it below the value story.
- Update the FAQ to answer:
  - why generic memory deletion is insufficient for derived data
  - what `deletion_verified` means
  - why the health-style demo exists

Suggested quickstart opening shape:

```md
Try the proof-first flow:
1. Remember a health event
2. Recall the derived context
3. Forget the source event
4. Verify the deleted detail does not resurface
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_public_launch_docs.py tests/unit/test_release_positioning.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add docs/quickstart.md docs/launch-faq.md tests/unit/test_public_launch_docs.py
git commit -m "docs: lead quickstart and faq with proof flow"
```

### Task 3: Simplify the client guides without changing the product

**Files:**
- Modify: `docs/guides/claude-code.md`
- Modify: `docs/guides/openclaw.md`
- Modify: `tests/unit/test_public_launch_docs.py`

**Step 1: Write the failing test**

Extend the client-guide coverage to check the simple user mental model.

```python
def test_client_guides_teach_remember_recall_forget_first() -> None:
    claude = (REPO_ROOT / "docs" / "guides" / "claude-code.md").read_text(encoding="utf-8").lower()
    openclaw = (REPO_ROOT / "docs" / "guides" / "openclaw.md").read_text(encoding="utf-8").lower()

    for doc in (claude, openclaw):
        assert "remember" in doc
        assert "recall" in doc
        assert "forget" in doc
        assert "deletion proof" in doc
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_public_launch_docs.py -q`
Expected: FAIL until both guides explicitly match the new teaching order.

**Step 3: Write minimal implementation**

- In `docs/guides/claude-code.md`, tighten the first paragraph so the guide answers:
  - what Orenyl gives Claude
  - what the first prompt sequence proves
- In `docs/guides/openclaw.md`, lead with the "remember / recall / forget" user value before the longer capability table.
- Keep the existing dev-only and production-auth caveats intact.

Suggested guide language:

```md
Orenyl gives your agent three immediate memory moves:
- remember new user context
- recall relevant facts
- forget a source memory and inspect the deletion proof
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_public_launch_docs.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add docs/guides/claude-code.md docs/guides/openclaw.md tests/unit/test_public_launch_docs.py
git commit -m "docs: simplify client guide onboarding story"
```

### Task 4: Run the release-doc verification sweep

**Files:**
- Review: `README.md`
- Review: `pyproject.toml`
- Review: `docs/quickstart.md`
- Review: `docs/launch-faq.md`
- Review: `docs/guides/claude-code.md`
- Review: `docs/guides/openclaw.md`
- Review: `docs/positioning.md`
- Review: `tests/unit/test_story_first_positioning.py`
- Review: `tests/unit/test_public_launch_docs.py`
- Review: `tests/unit/test_release_positioning.py`
- Review: `tests/unit/test_release_metadata.py`
- Review: `tests/unit/test_readme_config_docs.py`

**Step 1: Run the verification suite**

Run:

```bash
python -m pytest tests/unit/test_story_first_positioning.py tests/unit/test_public_launch_docs.py tests/unit/test_release_positioning.py tests/unit/test_release_metadata.py tests/unit/test_readme_config_docs.py -q
```

Expected: PASS

**Step 2: Fix any brittle assertions or copy regressions**

If a failure is caused by:

- missing beta-honest wording, restore it
- broken config-table expectations, fix the README carefully without touching defaults
- overly brittle new tests, loosen them to protect the story rather than exact prose

**Step 3: Re-run the verification suite**

Run the same command again.
Expected: PASS

**Step 4: Sanity-check the main reading path manually**

Review the first screen of each public entry point in this order:

1. `README.md`
2. `docs/quickstart.md`
3. `docs/guides/claude-code.md`
4. `docs/guides/openclaw.md`
5. `pyproject.toml`

Confirm each one answers:

- what is the problem?
- what does Orenyl do?
- what proof should the evaluator look for?

**Step 5: Commit**

```bash
git add README.md pyproject.toml docs/quickstart.md docs/launch-faq.md docs/guides/claude-code.md docs/guides/openclaw.md docs/positioning.md tests/unit/test_story_first_positioning.py tests/unit/test_public_launch_docs.py
git commit -m "docs: align launch surfaces around proof-first story"
```
