from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_release_checklist_covers_the_current_release_contract() -> None:
    doc = (REPO_ROOT / "docs" / "RELEASE_CHECKLIST.md").read_text(encoding="utf-8")
    lower = doc.lower()
    process_doc = (REPO_ROOT / "docs" / "RELEASE_PROCESS.md").read_text(encoding="utf-8")
    process_prefix = "\n".join(process_doc.splitlines()[:4]).lower()

    for heading in [
        "## Ship posture",
        "## Preconditions",
        "## Local verification",
        "## CI / tagged-release verification",
        "## Release artifacts to inspect",
        "## Rollback / hotfix path",
    ]:
        assert heading in doc

    assert "for the exact pre-tag checklist, see [release_checklist.md](release_checklist.md)." in process_prefix
    assert "use it for every public beta / early-production release." in process_prefix
    assert "bootstrap the release tools" in lower
    assert "bootstrap" in lower
    assert "bandit" in lower
    assert "pip-audit" in lower
    assert "pytest-cov" in lower
    assert "build" in lower
    assert "mypy" in lower
    assert "python -m pip install bandit pip-audit pytest-cov build mypy" in doc
    assert "python -m pip install --no-deps -e ." in doc
    assert "python scripts/verify_release.py" in doc
    assert doc.index("python -m pip install bandit pip-audit pytest-cov build mypy") < doc.index("python -m pip install --no-deps -e .")
    assert doc.index("python -m pip install --no-deps -e .") < doc.index("python scripts/verify_release.py")
    assert "clean working tree" in lower
    assert "release artifacts" in lower
    assert "rollback" in lower
    assert "same release verifier" not in lower
