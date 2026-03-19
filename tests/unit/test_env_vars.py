from lore import env_vars


def test_all_env_var_names_are_unique_and_lore_prefixed():
    names = env_vars.all_names()

    assert names
    assert len(names) == len(set(names))
    assert all(name.startswith("LORE_") for name in names)


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
