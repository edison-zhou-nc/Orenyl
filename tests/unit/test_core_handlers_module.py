from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta

import pytest

from orenyl import server
from orenyl.db import Database
from orenyl.handlers import core
from orenyl.handlers.core import MAX_EXPORT_DOMAIN_EVENTS, handle_store_event
from orenyl.lineage import LineageEngine


class _EmbeddingProviderStub:
    provider_id = "test-provider"

    def embed_text(self, _text: str) -> list[float]:
        return [0.1, 0.2, 0.3]


def _install_core_runtime(monkeypatch) -> Database:
    db = Database(":memory:")
    monkeypatch.setattr(core, "get_db", lambda: db)
    monkeypatch.setattr(core, "get_engine", lambda: LineageEngine(db))
    monkeypatch.setattr(core, "get_embedding_provider", lambda: _EmbeddingProviderStub())
    monkeypatch.setattr(core, "backfill_missing_fact_embeddings", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(core, "_runtime_encryption_material", lambda: None)
    return db

def test_server_re_exports_core_handlers():
    assert server.handle_store_event is handle_store_event


def test_store_event_rejects_non_list_domains(monkeypatch):
    _install_core_runtime(monkeypatch)

    result = asyncio.run(core.handle_store_event({"content": "test", "domains": "not-a-list"}))

    payload = json.loads(result[0].text)
    assert payload["error"] == "invalid_domains"


def test_store_event_rejects_empty_domains(monkeypatch):
    _install_core_runtime(monkeypatch)

    result = asyncio.run(core.handle_store_event({"content": "test", "domains": []}))

    payload = json.loads(result[0].text)
    assert payload["error"] == "invalid_domains"


def test_store_event_rejects_excessive_domains(monkeypatch):
    _install_core_runtime(monkeypatch)

    result = asyncio.run(core.handle_store_event({"content": "test", "domains": ["d"] * 101}))

    payload = json.loads(result[0].text)
    assert payload["error"] == "too_many_domains"


def test_store_event_rejects_invalid_type(monkeypatch):
    _install_core_runtime(monkeypatch)

    result = asyncio.run(
        core.handle_store_event(
            {"content": "test", "domains": ["general"], "type": "x" * 200},
        )
    )

    payload = json.loads(result[0].text)
    assert payload["error"] == "invalid_type"


def test_store_event_rejects_future_timestamp(monkeypatch):
    _install_core_runtime(monkeypatch)
    future = (datetime.now(UTC) + timedelta(days=365)).isoformat()

    result = asyncio.run(
        core.handle_store_event({"content": "test", "domains": ["general"], "ts": future})
    )

    payload = json.loads(result[0].text)
    assert payload["error"] == "invalid_timestamp"


def test_export_domain_rejects_oversized_domain_before_loading(monkeypatch):
    db = Database(":memory:")
    monkeypatch.setattr(core, "get_db", lambda: db)
    monkeypatch.setattr(
        db,
        "get_event_count",
        lambda domain="general", tenant_id="": MAX_EXPORT_DOMAIN_EVENTS + 1,
        raising=False,
    )
    monkeypatch.setattr(
        db,
        "get_active_events_by_domains",
        lambda *_args, **_kwargs: pytest.fail("should not materialize events for oversized export"),
        raising=False,
    )
    monkeypatch.setattr(
        db,
        "get_active_events",
        lambda *_args, **_kwargs: pytest.fail("should not materialize events for oversized export"),
        raising=False,
    )
    monkeypatch.setattr(
        db,
        "get_current_facts_by_domain",
        lambda *_args, **_kwargs: pytest.fail("should not materialize facts for oversized export"),
        raising=False,
    )

    result = asyncio.run(core.handle_export_domain({"domain": "huge"}))

    payload = json.loads(result[0].text)
    assert payload["error"] == "export_domain_too_large"


def test_export_domain_general_requires_bounded_export(monkeypatch):
    db = Database(":memory:")
    monkeypatch.setattr(core, "get_db", lambda: db)
    monkeypatch.setattr(
        db,
        "get_event_count",
        lambda domain="general", tenant_id="": MAX_EXPORT_DOMAIN_EVENTS + 1,
        raising=False,
    )
    monkeypatch.setattr(
        db,
        "get_active_events",
        lambda *_args, **_kwargs: pytest.fail("general export should be size-checked first"),
        raising=False,
    )
    monkeypatch.setattr(
        db,
        "get_current_facts_by_domain",
        lambda *_args, **_kwargs: pytest.fail("general export should be size-checked first"),
        raising=False,
    )

    result = asyncio.run(core.handle_export_domain({"domain": "general"}))

    payload = json.loads(result[0].text)
    assert payload["error"] == "export_domain_too_large"
