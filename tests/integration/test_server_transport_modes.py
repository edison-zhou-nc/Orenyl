import pytest

from lore import server
def test_default_transport_is_streamable_http_for_prod(monkeypatch):
    monkeypatch.delenv("LORE_TRANSPORT", raising=False)
    assert server.get_transport_mode() == "streamable-http"


def test_stdio_mode_allowed_only_with_explicit_dev_flag(monkeypatch):
    monkeypatch.setenv("LORE_TRANSPORT", "stdio")
    monkeypatch.delenv("LORE_ALLOW_STDIO_DEV", raising=False)

    with pytest.raises(PermissionError, match="LORE_ALLOW_STDIO_DEV=1"):
        server.validate_transport_mode(server.get_transport_mode())

    monkeypatch.setenv("LORE_ALLOW_STDIO_DEV", "1")
    server.validate_transport_mode(server.get_transport_mode())

