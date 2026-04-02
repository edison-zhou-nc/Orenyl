from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_release_checklist_exists_and_covers_ship_now_gate() -> None:
    doc = (REPO_ROOT / "docs" / "RELEASE_CHECKLIST.md").read_text(encoding="utf-8")

    assert "public beta / early production" in doc.lower()
    assert "python scripts/verify_release.py" in doc
    assert "clean working tree" in doc.lower()
    assert "release artifacts" in doc.lower()
    assert "rollback" in doc.lower()
