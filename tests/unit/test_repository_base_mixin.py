from lore.repositories._base import BaseMixin


def test_base_mixin_exposes_commit_helper():
    assert hasattr(BaseMixin, "_maybe_commit")
