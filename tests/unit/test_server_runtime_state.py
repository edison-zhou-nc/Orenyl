import pytest
from pathlib import Path

from lore import context_pack as context_pack_module
from lore import server
from lore.context_pack import ContextPackBuilder
from lore.db import Database
from lore.lazy import Lazy
from lore.lineage import LineageEngine
from lore.models import Event


def test_reset_runtime_state_clears_verifier_and_salt_warning(monkeypatch):
    created = {"count": 0}

    def _build_provider() -> object:
        created["count"] += 1
        return object()

    monkeypatch.setattr(server, "_token_verifier", object())
    monkeypatch.setattr(server, "_token_verifier_error", RuntimeError("misconfigured"))
    monkeypatch.setattr(server, "_DEFAULT_SALT_WARNING_EMITTED", True)
    monkeypatch.setattr(
        context_pack_module, "_embedding_provider_lazy", Lazy(lambda: object())
    )
    monkeypatch.setattr(context_pack_module, "_vector_backend", object())
    patched_lazy = Lazy(_build_provider)
    monkeypatch.setattr(server, "_embedding_provider_lazy", patched_lazy)

    first = server._get_embedding_provider()

    server._reset_runtime_state_for_tests()
    second = server._get_embedding_provider()

    assert server._token_verifier is None
    assert server._token_verifier_error is None
    assert server._DEFAULT_SALT_WARNING_EMITTED is False
    assert context_pack_module._vector_backend is None
    assert first is not second
    assert created["count"] == 2


def test_embedding_provider_is_cached_only_via_lazy_wrapper():
    assert not hasattr(context_pack_module, "_embedding_provider")
    assert not hasattr(server, "embedding_provider")


def test_get_token_verifier_caches_build_runtime_error(monkeypatch):
    attempts = {"count": 0}

    def _raise_misconfigured():
        attempts["count"] += 1
        raise RuntimeError("misconfigured")

    server._reset_runtime_state_for_tests()
    monkeypatch.setattr(server, "build_token_verifier_from_env", _raise_misconfigured)

    with pytest.raises(RuntimeError, match="misconfigured"):
        server._get_token_verifier()
    with pytest.raises(RuntimeError, match="misconfigured"):
        server._get_token_verifier()

    assert attempts["count"] == 1
    assert isinstance(server._token_verifier_error, RuntimeError)


def test_rebind_runtime_state_for_tests_rebinds_database_path_from_env(monkeypatch, tmp_path):
    seeded_db = tmp_path / "seeded.db"
    fresh_db = tmp_path / "fresh.db"

    seeded = Database(str(seeded_db))
    seeded.insert_event(Event(id="event:test:seeded", type="note", payload={"text": "seeded"}))
    monkeypatch.setattr(server, "db", seeded)
    monkeypatch.setattr(server, "engine", LineageEngine(seeded))
    monkeypatch.setattr(server, "pack_builder", ContextPackBuilder(seeded))
    monkeypatch.setattr(server, "DB_PATH", str(seeded_db))
    monkeypatch.setenv("LORE_DB_PATH", str(fresh_db))

    server._rebind_runtime_state_for_tests()

    payload = server.db.get_active_events()
    assert payload == []


def test_server_does_not_alias_context_pack_test_reset_helper_at_import_time():
    import lore.server as server_module

    assert not hasattr(server_module, "reset_context_pack_runtime_state_for_tests")
