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
