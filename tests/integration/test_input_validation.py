import asyncio
import json
from datetime import UTC, datetime, timedelta

import pytest

from orenyl import server
from orenyl.context_pack import ContextPackBuilder
from orenyl.db import Database
from orenyl.lineage import LineageEngine


def _reset_server(monkeypatch):
    fresh_db = Database(":memory:")
    monkeypatch.setattr(server, "db", fresh_db)
    monkeypatch.setattr(server, "engine", LineageEngine(fresh_db))
    monkeypatch.setattr(server, "pack_builder", ContextPackBuilder(fresh_db))


def test_store_event_rejects_unknown_sensitivity(monkeypatch):
    _reset_server(monkeypatch)

    out = asyncio.run(
        server.handle_store_event(
            {
                "domains": ["general"],
                "type": "note",
                "payload": {"text": "hello"},
                "sensitivity": "secret",
            }
        )
    )
    payload = json.loads(out[0].text)

    assert payload["stored"] is False
    assert payload["reason"] == "invalid_sensitivity"


def test_store_event_rejects_oversized_metadata(monkeypatch):
    _reset_server(monkeypatch)

    out = asyncio.run(
        server.handle_store_event(
            {
                "domains": ["general"],
                "type": "note",
                "content": "hello world",
                "metadata": {"blob": "x" * 70_000},
            }
        )
    )
    payload = json.loads(out[0].text)

    assert payload["stored"] is False
    assert payload["reason"] == "metadata_too_large"


def test_store_event_rejects_falsey_non_dict_metadata(monkeypatch):
    _reset_server(monkeypatch)

    out = asyncio.run(
        server.handle_store_event(
            {
                "domains": ["general"],
                "type": "note",
                "content": "hello world",
                "metadata": [],
            }
        )
    )
    payload = json.loads(out[0].text)

    assert payload["stored"] is False
    assert payload["reason"] == "invalid_metadata"


def test_store_event_rejects_future_timestamp(monkeypatch):
    _reset_server(monkeypatch)
    future = (datetime.now(UTC) + timedelta(hours=25)).strftime("%Y-%m-%dT%H:%M:%SZ")

    out = asyncio.run(
        server.handle_store_event(
            {
                "domains": ["general"],
                "type": "note",
                "content": "hello world",
                "ts": future,
            }
        )
    )
    payload = json.loads(out[0].text)

    assert payload["stored"] is False
    assert payload["reason"] == "invalid_timestamp"
    assert "future" in payload["detail"]


def test_store_event_rejects_timestamp_older_than_ten_years(monkeypatch):
    _reset_server(monkeypatch)
    too_old = (datetime.now(UTC) - timedelta(days=365 * 11)).strftime("%Y-%m-%dT%H:%M:%SZ")

    out = asyncio.run(
        server.handle_store_event(
            {
                "domains": ["general"],
                "type": "note",
                "content": "hello world",
                "ts": too_old,
            }
        )
    )
    payload = json.loads(out[0].text)

    assert payload["stored"] is False
    assert payload["reason"] == "invalid_timestamp"
    assert "past" in payload["detail"]


def test_delete_and_recompute_rejects_unknown_target_type(monkeypatch):
    _reset_server(monkeypatch)

    with pytest.raises(ValueError, match="invalid_target_type"):
        asyncio.run(
            server.handle_delete_and_recompute(
                {
                    "target_id": "event:test",
                    "target_type": "mystery",
                }
            )
        )
