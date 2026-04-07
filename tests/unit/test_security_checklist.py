from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_security_audit_doc_exists_and_covers_ga_checklist() -> None:
    doc = (REPO_ROOT / "docs" / "SECURITY_AUDIT.md").read_text()

    assert "auth coverage" in doc.lower()
    assert "fail-closed" in doc.lower()
    assert "config hygiene" in doc.lower()
    assert "ci" in doc.lower()
    assert "s105" in doc.lower()


def test_security_audit_lists_operator_responsibilities() -> None:
    doc = (REPO_ROOT / "docs" / "SECURITY_AUDIT.md").read_text(encoding="utf-8").lower()

    assert "repo-owned vs operator-owned boundary" in doc
    assert "repo-owned controls cover the code, docs, and tests in this repository." in doc
    assert "### operator responsibilities" in doc
    assert "oidc" in doc
    assert "secrets" in doc
    assert "backups" in doc
