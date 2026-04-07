from orenyl import metrics


def test_metrics_concurrent_increments_are_counted_correctly():
    import threading

    metrics.reset_metrics_for_tests()

    threads: list[threading.Thread] = []
    thread_count = 8
    increments_per_thread = 2000

    def _worker():
        for _ in range(increments_per_thread):
            metrics.inc_tool_call("store_event", "ok")

    for _ in range(thread_count):
        t = threading.Thread(target=_worker)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    rendered = metrics.render_prometheus()
    expected_total = thread_count * increments_per_thread
    assert f"orenyl_tool_calls_total {expected_total}" in rendered
    assert f'orenyl_tool_calls{{tool="store_event",status="ok"}} {expected_total}' in rendered


def test_latency_observations_are_bounded():
    metrics.reset_metrics_for_tests()

    for i in range(20_000):
        metrics.observe_latency("store_event_latency_ms", float(i))

    rendered = metrics.render_prometheus()

    assert "orenyl_store_event_latency_ms_count 10000" in rendered
