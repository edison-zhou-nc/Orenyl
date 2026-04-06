import threading

from orenyl.lazy import Lazy


def test_lazy_caches_until_reset():
    calls = {"count": 0}

    def build_value() -> object:
        calls["count"] += 1
        return object()

    lazy = Lazy(build_value)

    first = lazy.value
    second = lazy.value

    assert first is second
    assert calls["count"] == 1

    lazy.reset()
    third = lazy.value

    assert third is not first
    assert calls["count"] == 2


def test_lazy_initializes_once_under_concurrency():
    calls = {"count": 0}
    barrier = threading.Barrier(8)

    def build_value() -> object:
        calls["count"] += 1
        return object()

    lazy = Lazy(build_value)
    results: list[object] = []
    errors: list[BaseException] = []
    lock = threading.Lock()

    def worker() -> None:
        try:
            barrier.wait(timeout=1.0)
            value = lazy.value
            with lock:
                results.append(value)
        except BaseException as exc:  # pragma: no cover - test helper guard
            with lock:
                errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=1.0)

    assert not errors
    assert len(results) == 8
    assert all(result is results[0] for result in results)
    assert calls["count"] == 1
