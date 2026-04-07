import sys
import types

from orenyl.db import Database
from orenyl.embeddings import encode_vector
from orenyl.models import Fact
from orenyl.vector_backend import LocalVectorBackend, PgvectorVectorBackend


def test_vector_backend_contract_returns_ordered_ids():
    db = Database(":memory:")
    vector_backend = LocalVectorBackend(db)
    db.insert_fact(Fact(id="fact:weak", key="k:weak", value={"v": "weak"}, tenant_id="tenant-a"))
    db.insert_fact(Fact(id="fact:best", key="k:best", value={"v": "best"}, tenant_id="tenant-a"))
    db.insert_fact(Fact(id="fact:next", key="k:next", value={"v": "next"}, tenant_id="tenant-a"))

    vector_backend.upsert(namespace="tenant-a", item_id="fact:weak", vector=[0.0, 1.0])
    vector_backend.upsert(namespace="tenant-a", item_id="fact:best", vector=[1.0, 0.0])
    vector_backend.upsert(namespace="tenant-a", item_id="fact:next", vector=[0.8, 0.2])

    ids = vector_backend.query(namespace="tenant-a", query=[1.0, 0.0], top_k=3)

    assert ids == ["fact:best", "fact:next", "fact:weak"]


def test_pgvector_backend_reuses_connection_until_closed(monkeypatch):
    created: list[object] = []

    class _Cursor:
        def __init__(self, conn):
            self.conn = conn
            self._rows: list[tuple[str, str]] = []

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, sql: str, params=None):
            self.conn.executed.append((sql, params))
            if sql.lstrip().startswith("SELECT"):
                self._rows = [("fact:best", encode_vector([1.0, 0.0]))]

        def fetchall(self):
            return list(self._rows)

    class _Conn:
        def __init__(self):
            self.closed = False
            self.commits = 0
            self.rollbacks = 0
            self.executed: list[tuple[str, object]] = []

        def cursor(self):
            return _Cursor(self)

        def commit(self):
            self.commits += 1

        def rollback(self):
            self.rollbacks += 1

        def close(self):
            self.closed = True

    def _connect(dsn: str, autocommit: bool = False):
        assert dsn == "postgresql://example"
        assert autocommit is False
        conn = _Conn()
        created.append(conn)
        return conn

    monkeypatch.setitem(sys.modules, "psycopg", types.SimpleNamespace(connect=_connect))
    backend = PgvectorVectorBackend(dsn="postgresql://example")

    backend.upsert(namespace="tenant-a", item_id="fact:best", vector=[1.0, 0.0])
    ids = backend.query(namespace="tenant-a", query=[1.0, 0.0], top_k=1)
    backend.close()
    backend.upsert(namespace="tenant-a", item_id="fact:next", vector=[0.8, 0.2])

    assert ids == ["fact:best"]
    assert len(created) == 2
    assert any("orenyl_vectors" in sql for sql, _params in created[0].executed)
    assert created[0].commits == 1
    assert created[0].closed is True
    assert created[1].commits == 1
