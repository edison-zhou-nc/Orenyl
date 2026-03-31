from __future__ import annotations

import json

from lore import audit
from lore.db import Database


def test_audit_log_hash_chain_detects_tamper():
    audit.clear_events()
    audit.log_security_event("list_events", "allow", principal_id="agent-a", request_id="req-1")
    audit.log_security_event("store_event", "deny", principal_id="agent-a", request_id="req-2")

    assert audit.verify_hash_chain() is True

    conn = audit._conn()
    conn.execute(
        "UPDATE security_audit_events SET details_json = ? WHERE request_id = ?",
        ('{"tampered":true}', "req-1"),
    )
    conn.commit()

    assert audit.verify_hash_chain() is False


def test_delete_retrieval_logs_for_lineage_uses_batched_selects():
    db = Database(":memory:")
    context_pack = json.dumps({"items": [{"id": "fact:test:match"}]})
    trace = json.dumps([{"item_id": "fact:test:match", "lineage": []}])
    for idx in range(2505):
        db.log_retrieval(
            query=f"q-{idx}",
            context_pack=context_pack if idx == 2504 else json.dumps({"items": []}),
            trace=trace if idx == 2504 else "[]",
        )

    class _ConnectionProxy:
        def __init__(self, inner):
            self._inner = inner
            self.select_sql: list[str] = []

        def execute(self, sql, params=()):
            if "SELECT id, context_pack, trace FROM retrieval_logs" in sql:
                self.select_sql.append(sql)
            return self._inner.execute(sql, params)

        def __getattr__(self, name):
            return getattr(self._inner, name)

    proxy = _ConnectionProxy(db.conn)
    db.conn = proxy

    deleted = db.delete_retrieval_logs_for_lineage(["fact:test:match"])

    assert deleted == 1
    assert any("LIMIT ? OFFSET ?" in sql for sql in proxy.select_sql)
