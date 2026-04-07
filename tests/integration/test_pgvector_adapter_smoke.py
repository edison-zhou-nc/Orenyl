import os

import pytest

from orenyl.vector_backend import PgvectorVectorBackend


@pytest.mark.skipif(
    os.environ.get("ORENYL_VECTOR_BACKEND", "").strip().lower() != "pgvector",
    reason="pgvector backend not enabled",
)
def test_pgvector_adapter_smoke():
    dsn = os.environ.get("ORENYL_PGVECTOR_DSN", "").strip()
    if not dsn:
        pytest.skip("ORENYL_PGVECTOR_DSN is not configured")

    backend = PgvectorVectorBackend(dsn=dsn)
    namespace = "tenant-smoke"
    item_id = "fact:smoke:vector"

    backend.upsert(namespace=namespace, item_id=item_id, vector=[0.1, 0.2, 0.3])
    ids = backend.query(namespace=namespace, query=[0.1, 0.2, 0.3], top_k=5)

    assert item_id in ids
