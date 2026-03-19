import pytest

from lore import context_pack as context_pack_module
from lore import server
from lore.lazy import Lazy


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
