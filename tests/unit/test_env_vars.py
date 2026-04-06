import pytest

from orenyl import env_vars


def test_all_env_var_names_are_unique_and_orenyl_prefixed():
    names = env_vars.all_names()

    assert names
    assert len(names) == len(set(names))
    assert all(name.startswith("ORENYL_") for name in names)


def test_all_env_var_names_exclude_prefix_constants():
    names = env_vars.all_names()

    assert env_vars.ENCRYPTION_PASSPHRASE_PREFIX not in names
    assert env_vars.ENCRYPTION_SALT_PREFIX not in names
    assert env_vars.SEMANTIC_DEDUP_THRESHOLD_PREFIX not in names


def test_all_prefixes_are_exposed_separately():
    prefixes = env_vars.all_prefixes()

    assert env_vars.ENCRYPTION_PASSPHRASE_PREFIX in prefixes
    assert env_vars.ENCRYPTION_SALT_PREFIX in prefixes
    assert env_vars.SEMANTIC_DEDUP_THRESHOLD_PREFIX in prefixes


def test_detect_legacy_names_returns_legacy_lore_keys(monkeypatch):
    monkeypatch.setenv("LORE_TRANSPORT", "stdio")
    monkeypatch.setenv("ORENYL_TRANSPORT", "streamable-http")
    monkeypatch.setenv("LORE_READ_ONLY_MODE", "1")

    assert env_vars.detect_legacy_names() == ("LORE_READ_ONLY_MODE", "LORE_TRANSPORT")


def test_require_no_legacy_env_vars_raises_for_legacy_keys(monkeypatch):
    monkeypatch.setenv("LORE_READ_ONLY_MODE", "1")

    with pytest.raises(RuntimeError, match="LORE_READ_ONLY_MODE"):
        env_vars.require_no_legacy_env_vars()
