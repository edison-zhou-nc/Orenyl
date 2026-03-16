from lore.repositories._base import BaseMixin


class _Conn:
    def __init__(self):
        self.commit_calls = 0

    def commit(self):
        self.commit_calls += 1


class _Repo(BaseMixin):
    def __init__(self, in_transaction: bool):
        self.conn = _Conn()
        self._in_transaction = in_transaction


def test_base_mixin_commits_only_outside_transactions():
    outside = _Repo(in_transaction=False)
    inside = _Repo(in_transaction=True)

    outside._maybe_commit()
    inside._maybe_commit()

    assert outside.conn.commit_calls == 1
    assert inside.conn.commit_calls == 0


def test_base_mixin_documents_commit_behavior():
    assert (
        BaseMixin._maybe_commit.__doc__
        == "Commit unless the repository is inside an explicit transaction."
    )
