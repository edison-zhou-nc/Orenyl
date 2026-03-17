"""Vector backend abstraction and adapters."""

from __future__ import annotations

from typing import Protocol

from .config import pgvector_dsn, vector_backend_name
from .db import Database
from .embeddings import cosine_similarity, decode_vector, encode_vector


class VectorBackend(Protocol):
    def upsert(self, namespace: str, item_id: str, vector: list[float]) -> None: ...

    def query(self, namespace: str, query: list[float], top_k: int) -> list[str]: ...


class LocalVectorBackend:
    """SQLite-backed vector store for local/dev usage."""

    def __init__(self, db: Database):
        self.db = db

    def upsert(self, namespace: str, item_id: str, vector: list[float]) -> None:
        self.db.upsert_fact_embedding(
            fact_id=item_id,
            vector=vector,
            model_id="vector-backend-local",
            tenant_id=namespace or "default",
        )

    def query(self, namespace: str, query: list[float], top_k: int) -> list[str]:
        rows = self.db.conn.execute(
            """SELECT fact_id, vector
               FROM fact_embeddings
               WHERE COALESCE(tenant_id, 'default') = ?""",
            (namespace or "default",),
        ).fetchall()
        scored: list[tuple[float, str]] = []
        for row in rows:
            item_id = str(row["fact_id"])
            vector = decode_vector(str(row["vector"]))
            scored.append((cosine_similarity(query, vector), item_id))
        scored.sort(key=lambda item: (-item[0], item[1]))
        safe_top_k = max(0, int(top_k))
        return [item_id for _, item_id in scored[:safe_top_k]]


class PgvectorVectorBackend:
    """pgvector adapter for externally managed Postgres vector stores."""

    def __init__(self, dsn: str):
        self.dsn = dsn

    def upsert(self, namespace: str, item_id: str, vector: list[float]) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """CREATE TABLE IF NOT EXISTS lore_vectors (
                           namespace TEXT NOT NULL,
                           item_id TEXT PRIMARY KEY,
                           embedding TEXT NOT NULL
                       )"""
                )
                cur.execute(
                    """INSERT INTO lore_vectors (namespace, item_id, embedding)
                       VALUES (%s, %s, %s)
                       ON CONFLICT (item_id) DO UPDATE SET
                         namespace = EXCLUDED.namespace,
                         embedding = EXCLUDED.embedding""",
                    (namespace, item_id, encode_vector(vector)),
                )
            conn.commit()

    def query(self, namespace: str, query: list[float], top_k: int) -> list[str]:
        # Fallback implementation uses client-side cosine scoring over JSON vectors.
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT item_id, embedding
                       FROM lore_vectors
                       WHERE namespace = %s""",
                    (namespace,),
                )
                rows = cur.fetchall()
        scored: list[tuple[float, str]] = []
        for item_id, embedding in rows:
            scored.append((cosine_similarity(query, decode_vector(str(embedding))), str(item_id)))
        scored.sort(key=lambda item: (-item[0], item[1]))
        return [item_id for _, item_id in scored[: max(0, int(top_k))]]

    def _connect(self):
        try:
            import psycopg
        except Exception as exc:  # pragma: no cover - exercised in pgvector environments only
            raise RuntimeError("pgvector_backend_requires_psycopg") from exc
        return psycopg.connect(self.dsn)


def build_vector_backend_from_env(db: Database) -> VectorBackend:
    backend = vector_backend_name()
    if backend == "pgvector":
        dsn = pgvector_dsn()
        if not dsn:
            raise RuntimeError("LORE_PGVECTOR_DSN is required when LORE_VECTOR_BACKEND=pgvector")
        return PgvectorVectorBackend(dsn=dsn)
    return LocalVectorBackend(db)
