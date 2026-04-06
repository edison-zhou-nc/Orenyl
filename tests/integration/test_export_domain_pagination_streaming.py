import asyncio
import hashlib
import json

import pytest

from orenyl import server
from orenyl.context_pack import ContextPackBuilder
from orenyl.db import Database
from orenyl.lineage import LineageEngine
from orenyl.models import Event


def _reset_server(monkeypatch, db):
    monkeypatch.setattr(server, "db", db)
    monkeypatch.setattr(server, "engine", LineageEngine(db))
    monkeypatch.setattr(server, "pack_builder", ContextPackBuilder(db))


def _seed_export_data(db):
    for idx in range(3):
        ev = Event(
            id=f"event:test:export:{idx}",
            type="diet_preference",
            payload={"value": f"v{idx}"},
            domains=["preferences"],
            ts=f"2026-01-01T00:00:0{idx}Z",
        )
        db.insert_event(ev)


def test_export_domain_supports_cursor_pagination(monkeypatch):
    db = Database(":memory:")
    _reset_server(monkeypatch, db)
    _seed_export_data(db)

    first = asyncio.run(
        server.handle_export_domain(
            {
                "domain": "preferences",
                "format": "json",
                "page_size": 2,
            }
        )
    )
    first_payload = json.loads(first[0].text)
    assert len(first_payload["items"]) == 2
    assert first_payload["has_more"] is True
    assert first_payload["next_cursor"]

    second = asyncio.run(
        server.handle_export_domain(
            {
                "domain": "preferences",
                "format": "json",
                "page_size": 2,
                "cursor": first_payload["next_cursor"],
            }
        )
    )
    second_payload = json.loads(second[0].text)
    assert len(second_payload["items"]) == 1
    assert second_payload["has_more"] is False

    first_ids = {item["id"] for item in first_payload["items"]}
    second_ids = {item["id"] for item in second_payload["items"]}
    assert first_ids.isdisjoint(second_ids)


def test_export_domain_stream_jsonl_includes_chunk_hash(monkeypatch):
    db = Database(":memory:")
    _reset_server(monkeypatch, db)
    _seed_export_data(db)

    out = asyncio.run(
        server.handle_export_domain(
            {
                "domain": "preferences",
                "format": "json",
                "stream": True,
                "page_size": 2,
                "include_hashes": True,
            }
        )
    )
    lines = [line for line in out[0].text.splitlines() if line.strip()]
    records = [json.loads(line) for line in lines]

    data_records = [record for record in records if record["kind"] == "record"]
    hash_records = [record for record in records if record["kind"] == "chunk_hash"]
    assert len(data_records) == 2
    assert len(hash_records) == 1

    canonical = "\n".join(
        json.dumps(record["item"], sort_keys=True, separators=(",", ":")) for record in data_records
    )
    expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    assert hash_records[0]["sha256"] == expected


def test_export_domain_pagination_guard_fails_fast_before_materialization(monkeypatch):
    db = Database(":memory:")
    _reset_server(monkeypatch, db)

    monkeypatch.setattr(
        db,
        "get_restricted_fact_ids_for_export_domain",
        lambda domain, tenant_id="": [],
        raising=False,
    )
    monkeypatch.setattr(db, "get_event_count", lambda domain="general", tenant_id="": 10001)
    monkeypatch.setattr(
        db,
        "get_active_events_by_domains",
        lambda *args, **kwargs: pytest.fail("should not materialize events before guard"),
    )
    monkeypatch.setattr(
        db,
        "get_active_events",
        lambda *args, **kwargs: pytest.fail("should not materialize events before guard"),
    )
    monkeypatch.setattr(
        db,
        "get_current_facts_by_domain",
        lambda *args, **kwargs: pytest.fail("should not materialize facts before guard"),
    )

    out = asyncio.run(
        server.handle_export_domain(
            {
                "domain": "preferences",
                "format": "json",
                "page_size": 10,
            }
        )
    )
    payload = json.loads(out[0].text)

    assert payload == {
        "error": "export_domain_too_large_for_pagination",
        "event_count": 10001,
    }


def test_export_domain_invalid_cursor_returns_stable_tool_error(monkeypatch):
    db = Database(":memory:")
    _reset_server(monkeypatch, db)
    _seed_export_data(db)
    monkeypatch.setenv("LORE_TRANSPORT", "stdio")
    monkeypatch.setenv("LORE_ALLOW_STDIO_DEV", "1")
    server._reset_runtime_state_for_tests()

    out = asyncio.run(
        server.call_tool(
            "export_domain",
            {
                "domain": "preferences",
                "format": "json",
                "page_size": 2,
                "cursor": "not-base64",
            },
        )
    )
    payload = json.loads(out[0].text)

    assert payload["error"] == "invalid_cursor"
