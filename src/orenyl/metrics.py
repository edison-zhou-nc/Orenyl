"""Minimal in-process metrics collection with Prometheus text rendering."""

from __future__ import annotations

import threading
from collections import defaultdict, deque

_COUNTERS: dict[tuple[str, ...], int] = defaultdict(int)
_MAX_LATENCY_OBSERVATIONS = 10_000
_LATENCIES: dict[str, deque[float]] = defaultdict(
    lambda: deque(maxlen=_MAX_LATENCY_OBSERVATIONS)
)
_LOCK = threading.Lock()


def reset_metrics_for_tests() -> None:
    with _LOCK:
        _COUNTERS.clear()
        _LATENCIES.clear()


def inc_tool_call(tool: str, status: str) -> None:
    with _LOCK:
        _COUNTERS[(tool, status)] += 1


def observe_latency(metric_name: str, ms: float) -> None:
    with _LOCK:
        _LATENCIES[metric_name].append(float(ms))


def render_prometheus() -> str:
    with _LOCK:
        counters = dict(_COUNTERS)
        latencies = {name: list(values) for name, values in _LATENCIES.items()}
    lines: list[str] = []
    total = sum(counters.values())
    lines.append(f"orenyl_tool_calls_total {total}")
    for (tool, status), value in sorted(counters.items()):
        lines.append(f'orenyl_tool_calls{{tool="{tool}",status="{status}"}} {value}')

    for name, values in sorted(latencies.items()):
        count = len(values)
        total_ms = sum(values)
        avg_ms = (total_ms / count) if count else 0.0
        lines.append(f"orenyl_{name}_count {count}")
        lines.append(f"orenyl_{name}_sum {total_ms:.6f}")
        lines.append(f"orenyl_{name}_avg {avg_ms:.6f}")
    return "\n".join(lines) + "\n"
