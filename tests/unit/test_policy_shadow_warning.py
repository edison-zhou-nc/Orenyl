import logging

import pytest

from orenyl.policy import (
    agent_permissions_enabled,
    policy_shadow_mode_enabled,
    validate_policy_configuration,
)


def test_shadow_mode_alone_emits_startup_warning(monkeypatch, caplog):
    """Shadow mode active without agent permissions should warn."""
    monkeypatch.setenv("ORENYL_POLICY_SHADOW_MODE", "1")
    monkeypatch.setenv("ORENYL_ENABLE_AGENT_PERMISSIONS", "0")
    monkeypatch.setenv("ORENYL_ENABLE_MULTI_TENANT", "0")

    with caplog.at_level(logging.WARNING):
        validate_policy_configuration()

    shadow_warnings = [
        record for record in caplog.records if "shadow_mode_active" in record.message
    ]
    assert len(shadow_warnings) == 1


def test_shadow_mode_with_agent_permissions_raises_without_multi_tenant(monkeypatch):
    """Shadow mode + agent permissions must hard-fail even in single-tenant mode."""
    monkeypatch.setenv("ORENYL_POLICY_SHADOW_MODE", "1")
    monkeypatch.setenv("ORENYL_ENABLE_AGENT_PERMISSIONS", "1")
    monkeypatch.setenv("ORENYL_ENABLE_MULTI_TENANT", "0")

    with pytest.raises(RuntimeError, match="cannot be enabled"):
        validate_policy_configuration()


def test_no_warning_when_shadow_mode_disabled(monkeypatch, caplog):
    """No warning when shadow mode is off."""
    monkeypatch.setenv("ORENYL_POLICY_SHADOW_MODE", "0")
    monkeypatch.setenv("ORENYL_ENABLE_AGENT_PERMISSIONS", "0")
    monkeypatch.setenv("ORENYL_ENABLE_MULTI_TENANT", "0")

    with caplog.at_level(logging.WARNING):
        validate_policy_configuration()

    assert not any("shadow_mode_active" in record.message for record in caplog.records)


def test_shadow_mode_with_multi_tenant_and_agent_perms_raises(monkeypatch):
    """The dangerous triple combination must still hard-fail."""
    monkeypatch.setenv("ORENYL_POLICY_SHADOW_MODE", "1")
    monkeypatch.setenv("ORENYL_ENABLE_AGENT_PERMISSIONS", "1")
    monkeypatch.setenv("ORENYL_ENABLE_MULTI_TENANT", "1")

    with pytest.raises(RuntimeError, match="cannot be enabled"):
        validate_policy_configuration()


def test_agent_permissions_enabled_rejects_legacy_env_vars(monkeypatch):
    with monkeypatch.context() as m:
        m.setenv("LORE_ENABLE_AGENT_PERMISSIONS", "1")

        with pytest.raises(RuntimeError, match="LORE_ENABLE_AGENT_PERMISSIONS"):
            agent_permissions_enabled()


def test_policy_shadow_mode_enabled_rejects_legacy_env_vars(monkeypatch):
    with monkeypatch.context() as m:
        m.setenv("LORE_POLICY_SHADOW_MODE", "1")

        with pytest.raises(RuntimeError, match="LORE_POLICY_SHADOW_MODE"):
            policy_shadow_mode_enabled()
