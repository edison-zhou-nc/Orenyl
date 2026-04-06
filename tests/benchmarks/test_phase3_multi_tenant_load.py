import os

import pytest

from orenyl.db import Database
from orenyl.models import Event


@pytest.mark.skipif(
    os.environ.get("LORE_ENABLE_PHASE3_LOAD_TEST", "").strip() != "1",
    reason="phase3 load benchmark is opt-in",
)
def test_phase3_multi_tenant_load():
    db = Database(":memory:")
    total_events = int(os.environ.get("LORE_PHASE3_LOAD_EVENTS", "1000000"))
    tenants = [f"tenant-{idx}" for idx in range(10)]

    for i in range(total_events):
        tenant_id = tenants[i % len(tenants)]
        db.insert_event(
            Event(
                id=f"event:bench:{i}",
                type="note",
                payload={"index": i},
                domains=["general"],
                tenant_id=tenant_id,
            )
        )

    sample = db.list_events_page(
        domains=["general"],
        include_tombstoned=False,
        limit=50,
        offset=0,
        tenant_id="tenant-0",
    )
    assert len(sample) > 0
