import pytest

from orenyl import context_pack as context_pack_module
from orenyl import env_vars, runtime, server
from orenyl.context_pack import ContextPackBuilder
from orenyl.db import Database
from orenyl.lazy import Lazy
from orenyl.lineage import LineageEngine
from orenyl.models import Event


def test_reset_runtime_state_clears_verifier_and_salt_warning(monkeypatch):
    created = {"count": 0}

    def _build_provider() -> object:
        created["count"] += 1
        return object()

    monkeypatch.setattr(server, "_token_verifier", object())
    monkeypatch.setattr(server, "_token_verifier_error", RuntimeError("misconfigured"))
    monkeypatch.setattr(server, "_DEFAULT_SALT_WARNING_EMITTED", True)
    monkeypatch.setattr(context_pack_module, "_vector_backend", object())
    patched_lazy = Lazy(_build_provider)
    monkeypatch.setattr(runtime, "_embedding_provider_lazy", patched_lazy)

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
    now = {"value": 1_000.0}

    def _raise_misconfigured():
        attempts["count"] += 1
        raise RuntimeError("misconfigured")

    server._reset_runtime_state_for_tests()
    monkeypatch.setattr(server, "build_token_verifier_from_env", _raise_misconfigured)
    monkeypatch.setattr(server.time, "time", lambda: now["value"])

    with pytest.raises(RuntimeError, match="misconfigured"):
        server._get_token_verifier()
    with pytest.raises(RuntimeError, match="misconfigured"):
        server._get_token_verifier()

    assert attempts["count"] == 1
    assert isinstance(server._token_verifier_error, RuntimeError)


def test_get_token_verifier_retries_build_runtime_error_after_ttl(monkeypatch):
    attempts = {"count": 0}
    now = {"value": 1_000.0}

    def _build_or_raise():
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("misconfigured")
        return object()

    server._reset_runtime_state_for_tests()
    monkeypatch.setattr(server, "build_token_verifier_from_env", _build_or_raise)
    monkeypatch.setattr(server.time, "time", lambda: now["value"])

    with pytest.raises(RuntimeError, match="misconfigured"):
        server._get_token_verifier()

    now["value"] += server._TOKEN_VERIFIER_ERROR_TTL + 1
    verifier = server._get_token_verifier()

    assert verifier is not None
    assert attempts["count"] == 2
    assert server._token_verifier_error is None


def test_rebind_runtime_state_for_tests_rebinds_database_path_from_env(monkeypatch, tmp_path):
    seeded_db = tmp_path / "seeded.db"
    fresh_db = tmp_path / "fresh.db"

    seeded = Database(str(seeded_db))
    seeded.insert_event(Event(id="event:test:seeded", type="note", payload={"text": "seeded"}))
    monkeypatch.setattr(server, "db", seeded)
    monkeypatch.setattr(server, "engine", LineageEngine(seeded))
    monkeypatch.setattr(server, "pack_builder", ContextPackBuilder(seeded))
    monkeypatch.setattr(server, "DB_PATH", str(seeded_db))
    monkeypatch.setenv("ORENYL_DB_PATH", str(fresh_db))

    server._rebind_runtime_state_for_tests()

    payload = server.db.get_active_events()
    assert payload == []


def test_runtime_state_test_helpers_require_testing_mode(monkeypatch, tmp_path):
    monkeypatch.delenv(env_vars.TESTING_MODE, raising=False)

    with pytest.raises(RuntimeError, match=env_vars.TESTING_MODE):
        server._rebind_runtime_state_for_tests(str(tmp_path / "guarded.db"))
    with pytest.raises(RuntimeError, match=env_vars.TESTING_MODE):
        server._reset_runtime_state_for_tests()


def test_server_does_not_alias_context_pack_test_reset_helper_at_import_time():
    import orenyl.server as server_module

    assert "reset_context_pack_runtime_state_for_tests" not in vars(server_module)


def test_vector_backend_cache_uses_stable_db_path(monkeypatch, tmp_path):
    created: list[str] = []

    def _build_backend(db: Database) -> object:
        created.append(str(getattr(db, "db_path", "")))
        return object()

    db_path = tmp_path / "shared.sqlite"
    same_path_a = Database(str(db_path))
    same_path_b = Database(str(db_path))
    other_path = Database(str(tmp_path / "other.sqlite"))

    context_pack_module._reset_runtime_state_for_tests()
    monkeypatch.setattr(context_pack_module, "build_vector_backend_from_env", _build_backend)

    first = context_pack_module._get_vector_backend(same_path_a)
    second = context_pack_module._get_vector_backend(same_path_b)
    third = context_pack_module._get_vector_backend(other_path)

    assert first is second
    assert third is not first
    assert created == [str(db_path), str(tmp_path / "other.sqlite")]


def test_get_federation_worker_initializes_once_under_concurrency(monkeypatch):
    created = {"count": 0}
    results: list[object] = []
    errors: list[BaseException] = []
    gate = __import__("threading").Barrier(8)
    lock = __import__("threading").Lock()

    class _Worker:
        def __init__(self, db, node_id):
            created["count"] += 1
            __import__("time").sleep(0.01)
            self.db = db
            self.node_id = node_id

    server._reset_runtime_state_for_tests()
    monkeypatch.setattr(server, "FederationWorker", _Worker)

    def _worker() -> None:
        try:
            gate.wait(timeout=1.0)
            worker = server._get_federation_worker()
            with lock:
                results.append(worker)
        except BaseException as exc:  # pragma: no cover - test helper guard
            with lock:
                errors.append(exc)

    threads = [__import__("threading").Thread(target=_worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=1.0)

    assert not errors
    assert len(results) == 8
    assert all(result is results[0] for result in results)
    assert created["count"] == 1
