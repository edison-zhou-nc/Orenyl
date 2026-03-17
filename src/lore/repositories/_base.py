"""Shared helpers for Database mixins."""

import sqlite3


class BaseMixin:
    conn: sqlite3.Connection
    _in_transaction: bool

    def _maybe_commit(self):
        """Commit unless the repository is inside an explicit transaction."""
        if not getattr(self, "_in_transaction", False):
            self.conn.commit()
