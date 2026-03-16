import asyncio

from lore import server


def test_run_ttl_sweep_includes_requested_mode(monkeypatch):
    class _FakeDB:
        def get_expired_events(self, _now: str):
            return []

    class _FakeEngine:
        def delete_and_recompute(self, *_args, **_kwargs):
            raise AssertionError("should not be called for empty expired set")

    monkeypatch.setattr(server, "db", _FakeDB())
    monkeypatch.setattr(server, "engine", _FakeEngine())

    out = server.run_ttl_sweep(delete_mode="hard")
    assert out["mode"] == "hard"
    assert out["count"] == 0


def test_periodic_ttl_sweep_runs_on_interval(monkeypatch):
    calls = []
    stop_event = asyncio.Event()

    def fake_run_ttl_sweep(delete_mode: str = "soft"):
        calls.append(delete_mode)
        if len(calls) >= 2:
            stop_event.set()
        return {"count": 0}

    monkeypatch.setattr(server, "run_ttl_sweep", fake_run_ttl_sweep)

    asyncio.run(server._ttl_sweep_loop(1, "soft", stop_event))

    assert len(calls) >= 2
    assert all(mode == "soft" for mode in calls)
