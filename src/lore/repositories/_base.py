"""Shared helpers for Database mixins."""


class BaseMixin:
    def _maybe_commit(self):
        """Commit unless the repository is inside an explicit transaction."""
        if not getattr(self, "_in_transaction", False):
            self.conn.commit()
