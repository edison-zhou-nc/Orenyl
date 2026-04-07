from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_compliance_readiness_doc_exists_and_covers_ga_checklist() -> None:
    doc = (REPO_ROOT / "docs" / "COMPLIANCE_READINESS.md").read_text()

    assert "gdpr" in doc.lower()
    assert "erasure" in doc.lower()
    assert "export" in doc.lower()
    assert "article 30" in doc.lower()
    assert "consent" in doc.lower()
    assert "retention" in doc.lower()
    assert "audit integrity" in doc.lower()
    assert "soc 2" in doc.lower()


def test_compliance_readiness_separates_repo_owned_from_external_readiness() -> None:
    doc = (REPO_ROOT / "docs" / "COMPLIANCE_READINESS.md").read_text(encoding="utf-8").lower()

    assert "repo-owned vs external readiness boundary" in doc
    assert "repo-owned readiness covers the code, tests, and documentation in this repository." in doc
    assert "deployment-specific controls" in doc
    assert "infrastructure" in doc
    assert "third-party validation" in doc
    assert "external certification" in doc or "externally certified" in doc
