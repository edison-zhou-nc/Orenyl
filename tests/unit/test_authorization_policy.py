import pytest

from orenyl.auth import authorize_action


def test_delete_requires_memory_delete_scope():
    with pytest.raises(PermissionError, match="missing_scope:memory:delete"):
        authorize_action({"memory:read"}, "delete_and_recompute")


def test_export_restricted_requires_memory_export_restricted_scope():
    with pytest.raises(PermissionError, match="missing_scope:memory:export:restricted"):
        authorize_action({"memory:export"}, "export_domain", restricted=True)
