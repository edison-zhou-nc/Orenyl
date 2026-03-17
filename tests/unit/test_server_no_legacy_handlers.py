"""Regression tests for the server handler extraction."""

from lore import server


def test_server_module_exposes_no_legacy_handlers() -> None:
    legacy_handlers = [name for name in dir(server) if name.startswith("_legacy_handle_")]

    assert legacy_handlers == []
