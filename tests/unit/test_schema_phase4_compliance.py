from __future__ import annotations

import asyncio
import json

import pytest

from orenyl.config import compliance_strict_mode_enabled, read_only_mode_enabled
from orenyl.db import Database
from orenyl.handlers import compliance as compliance_handlers
from orenyl.models import AuditChainRecord, ConsentRecord, DRSnapshot, SubjectRequest


def test_phase4_tables_exist(tmp_path):
    db = Database(str(tmp_path / "orenyl.db"))
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


def test_record_consent_rejects_invalid_status(monkeypatch):
    monkeypatch.setattr(
        compliance_handlers,
        "get_consent_service",
        lambda: pytest.fail("invalid status should fail before service call"),
    )

    result = asyncio.run(
        compliance_handlers.handle_record_consent(
            {"subject_id": "user-1", "purpose": "retrieval", "status": "gibberish"}
        )
    )

    payload = json.loads(result[0].text)
    assert payload["error"] == "invalid_consent_status"


def test_record_consent_accepts_valid_statuses(monkeypatch):
    recorded: list[str] = []

    class _ConsentService:
        def record(self, **kwargs):
            recorded.append(kwargs["status"])
            return f"consent:{kwargs['status']}"

    monkeypatch.setattr(compliance_handlers, "get_consent_service", lambda: _ConsentService())

    for status in ["granted", "denied", "withdrawn", "pending"]:
        result = asyncio.run(
            compliance_handlers.handle_record_consent(
                {"subject_id": "user-1", "purpose": "retrieval", "status": status}
            )
        )
        payload = json.loads(result[0].text)
        assert payload["ok"] is True

    assert recorded == ["granted", "denied", "withdrawn", "pending"]


def test_erase_subject_data_rejects_empty_id(monkeypatch):
    monkeypatch.setattr(
        compliance_handlers,
        "get_compliance_service",
        lambda: pytest.fail("missing subject_id should fail before service call"),
    )

    result = asyncio.run(compliance_handlers.handle_erase_subject_data({"subject_id": ""}))

    payload = json.loads(result[0].text)
    assert payload["error"] == "subject_id_required"


def test_erase_subject_data_rejects_missing_id(monkeypatch):
    monkeypatch.setattr(
        compliance_handlers,
        "get_compliance_service",
        lambda: pytest.fail("missing subject_id should fail before service call"),
    )

    result = asyncio.run(compliance_handlers.handle_erase_subject_data({}))

    payload = json.loads(result[0].text)
    assert payload["error"] == "subject_id_required"
