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
            sql = sql.strip()
            if sql.startswith("SELECT to_regclass"):
                regclass = params[0] if params else sql.split("'")[1]
                if regclass.startswith("public."):
                    self._rows = [(None,)]
                    return
                table_name = regclass.split(".")[-1]
                self._rows = [(table_name,)] if table_name in self.conn.tables else [(None,)]
                return
            if sql.startswith("CREATE TABLE IF NOT EXISTS orenyl_vectors"):
                self.conn.tables.add("orenyl_vectors")
                return
            if sql.startswith("INSERT INTO orenyl_vectors"):
                self.conn.tables.add("orenyl_vectors")
                return
            if sql.startswith("SELECT item_id, embedding"):
                self._rows = [("fact:best", encode_vector([1.0, 0.0]))]

        def fetchone(self):
            return self._rows[0] if self._rows else None

        def fetchall(self):
            return list(self._rows)

    class _Conn:
        def __init__(self):
            self.closed = False
            self.commits = 0
            self.rollbacks = 0
            self.executed: list[tuple[str, object]] = []
            self.tables = set()

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
    assert created[0].commits >= 1
    assert created[0].closed is True
    assert created[1].commits >= 1


def test_pgvector_backend_honors_search_path_for_legacy_table_upgrade(monkeypatch):
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
            sql = sql.strip()
            if sql.startswith("SELECT to_regclass"):
                table_name = params[0] if params else sql.split("'")[1]
                self._rows = [(table_name,)] if table_name in self.conn.tables else [(None,)]
                return
            if sql.startswith("ALTER TABLE lore_vectors RENAME TO orenyl_vectors"):
                self.conn.tables["orenyl_vectors"] = self.conn.tables.pop("lore_vectors")
                return
            if sql.startswith("CREATE TABLE IF NOT EXISTS orenyl_vectors"):
                self.conn.tables.setdefault("orenyl_vectors", [])
                return
            if sql.startswith("INSERT INTO orenyl_vectors") and "SELECT" in sql:
                legacy_rows = self.conn.tables.get("lore_vectors", [])
                target = self.conn.tables.setdefault("orenyl_vectors", [])
                for row in legacy_rows:
                    target.append(row)
                return
            if sql.startswith("INSERT INTO orenyl_vectors"):
                namespace, item_id, embedding = params
                table = self.conn.tables.setdefault("orenyl_vectors", [])
                table[:] = [row for row in table if row[1] != item_id]
                table.append((namespace, item_id, embedding))
                return
            if sql.startswith("SELECT item_id, embedding"):
                namespace = params[0]
                rows = self.conn.tables.get("orenyl_vectors", [])
                self._rows = [
                    (item_id, embedding) for ns, item_id, embedding in rows if ns == namespace
                ]

        def fetchone(self):
            return self._rows[0] if self._rows else None

        def fetchall(self):
            return list(self._rows)

    class _Conn:
        def __init__(self):
            self.closed = False
            self.commits = 0
            self.rollbacks = 0
            self.executed: list[tuple[str, object]] = []
            self.tables = {"lore_vectors": [("tenant-a", "fact:legacy", encode_vector([1.0, 0.0]))]}

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

    ids = backend.query(namespace="tenant-a", query=[1.0, 0.0], top_k=1)

    assert ids == ["fact:legacy"]
    assert len(created) == 1
    assert ("SELECT to_regclass(%s)", ("orenyl_vectors",)) in created[0].executed
    assert ("SELECT to_regclass(%s)", ("lore_vectors",)) in created[0].executed
    assert "lore_vectors" not in created[0].tables
    assert "orenyl_vectors" in created[0].tables
