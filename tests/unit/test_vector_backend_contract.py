from lore.db import Database
from lore.models import Fact
from lore.vector_backend import LocalVectorBackend


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
