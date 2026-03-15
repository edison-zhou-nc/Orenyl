"""Shared helpers for Database mixins."""


class BaseMixin:
    def _maybe_commit(self):
        if not getattr(self, "_in_transaction", False):
            self.conn.commit()
