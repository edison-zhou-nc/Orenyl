"""Simple audit anomaly detection rules."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any


def scan_access_anomalies(
    events: list[dict[str, Any]],
    window_minutes: int = 60,
) -> list[dict[str, Any]]:
    cutoff = datetime.now(UTC) - timedelta(minutes=max(1, int(window_minutes)))
    scoped_events: list[dict[str, Any]] = []
    for event in events:
        raw_ts = str(event.get("ts", "")).strip()
        if not raw_ts:
            continue
        try:
            parsed = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
        except ValueError:
            continue
        if parsed >= cutoff:
            scoped_events.append(event)
    events = scoped_events
    if not events:
        return []
    result_counts = Counter(str(event.get("result", "")).lower() for event in events)
    action_counts = Counter(str(event.get("action", "")) for event in events)
    deny_count = result_counts.get("deny", 0)
    total = len(events)
    alerts: list[dict[str, Any]] = []

    deny_ratio = deny_count / total
    if deny_count >= 5 and deny_ratio >= 0.5:
        alerts.append(
            {
                "type": "deny_spike",
                "severity": "high" if deny_ratio >= 0.75 else "medium",
                "deny_count": deny_count,
                "total_events": total,
                "deny_ratio": round(deny_ratio, 3),
                "window_minutes": int(window_minutes),
            }
        )

    if action_counts:
        hottest_action, hottest_count = action_counts.most_common(1)[0]
        if hottest_count >= max(8, int(total * 0.8)):
            alerts.append(
                {
                    "type": "single_action_dominance",
                    "severity": "medium",
                    "action": hottest_action,
                    "count": hottest_count,
                    "total_events": total,
                }
            )

    return alerts
