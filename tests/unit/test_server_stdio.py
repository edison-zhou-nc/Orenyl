from __future__ import annotations

import asyncio

from orenyl import server_stdio


def test_server_stdio_main_validates_mode_and_runs_stdio(monkeypatch):
    seen: dict[str, object] = {}

    async def _fake_run_stdio_server():
        return None

    def _fake_get_transport_mode() -> str:
        return "stdio"

    def _fake_validate_transport_mode(mode: str) -> None:
        seen["mode"] = mode

    def _fake_asyncio_run(coro):
        seen["ran"] = True
        seen["is_coroutine"] = asyncio.iscoroutine(coro)
        coro.close()

    monkeypatch.setattr(server_stdio, "get_transport_mode", _fake_get_transport_mode)
    monkeypatch.setattr(server_stdio, "validate_transport_mode", _fake_validate_transport_mode)
    monkeypatch.setattr(server_stdio, "run_stdio_server", _fake_run_stdio_server)
    monkeypatch.setattr(server_stdio.asyncio, "run", _fake_asyncio_run)

    server_stdio.main()

    assert seen == {"mode": "stdio", "ran": True, "is_coroutine": True}
