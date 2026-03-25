import logging

from lore import server


def test_server_warns_when_shadow_mode_is_active(caplog, monkeypatch):
    caplog.set_level(logging.WARNING)
    monkeypatch.setenv("LORE_ENABLE_MULTI_TENANT", "0")
    monkeypatch.setenv("LORE_ENABLE_AGENT_PERMISSIONS", "1")
    monkeypatch.setenv("LORE_POLICY_SHADOW_MODE", "1")

    server._warn_on_risky_policy_configuration()

    assert any("policy_shadow_mode_active" in record.message for record in caplog.records)
