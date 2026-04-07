from __future__ import annotations

import pytest

from orenyl import audit


def test_audit_module_rejects_legacy_env_vars(monkeypatch):
    with monkeypatch.context() as m:
        m.setenv("LORE_AUDIT_DB_PATH", "lore_audit.db")
        audit._reset_for_tests()

        with pytest.raises(RuntimeError, match="LORE_AUDIT_DB_PATH"):
            audit.clear_events()


def test_audit_module_rejects_legacy_env_vars_with_warm_connection(monkeypatch):
    audit._reset_for_tests()
    audit.clear_events()

    with monkeypatch.context() as m:
        m.setenv("LORE_AUDIT_DB_PATH", "lore_audit.db")

        with pytest.raises(RuntimeError, match="LORE_AUDIT_DB_PATH"):
            audit.clear_events()
