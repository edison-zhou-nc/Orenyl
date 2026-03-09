import pytest

from lore import server


def test_reset_runtime_state_clears_verifier_and_salt_warning(monkeypatch):
    monkeypatch.setattr(server, "_token_verifier", object())
    monkeypatch.setattr(server, "_token_verifier_error", RuntimeError("misconfigured"))
    monkeypatch.setattr(server, "_DEFAULT_SALT_WARNING_EMITTED", True)

    server._reset_runtime_state_for_tests()

    assert server._token_verifier is None
    assert server._token_verifier_error is None
    assert server._DEFAULT_SALT_WARNING_EMITTED is False


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
