import json

from lore.db import Database


def _seed_event(db: Database, event_id: str, tenant_id: str, domain: str = "health") -> None:
    db.conn.execute(
        """INSERT INTO events (
               id, type, payload, content_hash, sensitivity, consent_source, expires_at, metadata,
               retention_tier, archived_at, agent_id, session_id, source, tenant_id, ts, valid_from, valid_to, created_at
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            event_id,
            "note",
            json.dumps({"text": event_id}),
            None,
            "medium",
            "implicit",
            None,
            "{}",
            "hot",
            None,
            "",
            "",
            "user",
            tenant_id,
            "2026-03-12T00:00:00Z",
            None,
            None,
            "2026-03-12T00:00:00Z",
        ),
    )
    db.conn.execute(
        "INSERT INTO event_domains (event_id, domain) VALUES (?, ?)", (event_id, domain)
    )


def _seed_fact(db: Database, fact_id: str, key: str, tenant_id: str) -> None:
    db.conn.execute(
        """INSERT INTO facts (
               id, key, value, transform_config, stale, importance, version,
               rule_id, rule_version, confidence, model_id, tenant_id, valid_from, valid_to, created_at
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            fact_id,
            key,
            json.dumps({"value": key}),
            "{}",
            0,
            0.5,
            1,
            "rule:test",
            "v1",
            1.0,
            "deterministic",
            tenant_id,
            "2026-03-12T00:00:00Z",
            None,
            "2026-03-12T00:00:00Z",
        ),
    )


def test_get_current_facts_by_domain_is_tenant_scoped():
    db = Database(":memory:")
    _seed_event(db, "event:test:tenant:a", "tenant-a")
    _seed_event(db, "event:test:tenant:b", "tenant-b")
    _seed_fact(db, "fact:tenant-a:f1", "tenant_a_key", "tenant-a")
    _seed_fact(db, "fact:tenant-b:f1", "tenant_b_key", "tenant-b")
    db.conn.execute(
        "INSERT INTO edges (tenant_id, parent_id, parent_type, child_id, child_type, relation) VALUES (?, ?, 'event', ?, 'fact', 'derived_from')",
        ("tenant-a", "event:test:tenant:a", "fact:tenant-a:f1"),
    )
    db.conn.execute(
        "INSERT INTO edges (tenant_id, parent_id, parent_type, child_id, child_type, relation) VALUES (?, ?, 'event', ?, 'fact', 'derived_from')",
        ("tenant-b", "event:test:tenant:b", "fact:tenant-b:f1"),
    )
    db.conn.commit()

    rows = db.get_current_facts_by_domain(domain="health", tenant_id="tenant-a")

    assert rows
    assert all(row["tenant_id"] == "tenant-a" for row in rows)
    assert {row["id"] for row in rows} == {"fact:tenant-a:f1"}


def test_get_events_by_domains_is_tenant_scoped():
    db = Database(":memory:")
    _seed_event(db, "event:test:tenant:events:a", "tenant-a")
    _seed_event(db, "event:test:tenant:events:b", "tenant-b")
    db.conn.commit()

    rows = db.get_events_by_domains(["health"], tenant_id="tenant-a")

    assert {row["id"] for row in rows} == {"event:test:tenant:events:a"}
    assert all(row["tenant_id"] == "tenant-a" for row in rows)


def test_lineage_query_does_not_traverse_across_tenants():
    db = Database(":memory:")
    db.conn.execute(
        "INSERT INTO edges (tenant_id, parent_id, parent_type, child_id, child_type, relation) VALUES (?, ?, 'event', ?, 'fact', 'derived_from')",
        ("tenant-a", "event:test:shared", "fact:tenant-a:1"),
    )
    db.conn.execute(
        "INSERT INTO edges (tenant_id, parent_id, parent_type, child_id, child_type, relation) VALUES (?, ?, 'event', ?, 'fact', 'derived_from')",
        ("tenant-b", "event:test:shared", "fact:tenant-b:1"),
    )
    db.conn.commit()

    downstream = db.get_downstream_facts(item_id="event:test:shared", tenant_id="tenant-a")

    assert downstream == ["fact:tenant-a:1"]


def test_event_embedding_read_write_is_tenant_scoped():
    db = Database(":memory:")
    _seed_event(db, "event:test:embed:a", "tenant-a")
    _seed_event(db, "event:test:embed:b", "tenant-b")
    db.conn.commit()

    db.upsert_event_embedding("event:test:embed:a", [0.1, 0.2], "model-test", tenant_id="tenant-a")
    db.upsert_event_embedding("event:test:embed:b", [0.2, 0.3], "model-test", tenant_id="tenant-b")

    tenant_a = db.get_event_embedding("event:test:embed:a", tenant_id="tenant-a")
    tenant_b_view = db.get_event_embedding("event:test:embed:b", tenant_id="tenant-a")

    assert tenant_a is not None
    assert tenant_a["tenant_id"] == "tenant-a"
    assert tenant_b_view is None
