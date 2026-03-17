import json

from lore.db import Database


def test_support_repositories_cover_sync_counts_and_retrieval_logs():
    db = Database(":memory:")

    assert (
        db.append_sync_journal_entry(
            tenant_id="tenant-support",
            direction="outbound",
            envelope_id="env-support",
            idempotency_key="idem-support",
            payload={"op": "upsert"},
        )
        is True
    )
    assert db.sync_journal_count("tenant-support") == 1

    db.log_retrieval(
        query="what changed",
        context_pack=json.dumps({"facts": []}),
        trace=json.dumps({"included": []}),
    )
    logs = db.get_retrieval_logs(limit=1)
    assert logs[0]["query"] == "what changed"
    assert logs[0]["context_pack"] == {"facts": []}
    assert logs[0]["trace"] == {"included": []}
