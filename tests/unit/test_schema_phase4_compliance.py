from __future__ import annotations

from lore.config import compliance_strict_mode_enabled, read_only_mode_enabled
from lore.db import Database
from lore.models import AuditChainRecord, ConsentRecord, DRSnapshot, SubjectRequest


def test_phase4_tables_exist(tmp_path):
    db = Database(str(tmp_path / "lore.db"))
    tables = {
        row[0]
        for row in db.conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    assert "consent_records" in tables
    assert "subject_requests" in tables
    assert "dr_snapshots" in tables


def test_phase4_models_exist():
    assert ConsentRecord is not None
    assert SubjectRequest is not None
    assert AuditChainRecord is not None
    assert DRSnapshot is not None


def test_phase4_config_defaults(monkeypatch):
    monkeypatch.delenv("LORE_COMPLIANCE_STRICT_MODE", raising=False)
    monkeypatch.delenv("LORE_READ_ONLY_MODE", raising=False)

    assert compliance_strict_mode_enabled() is True
    assert read_only_mode_enabled() is False
