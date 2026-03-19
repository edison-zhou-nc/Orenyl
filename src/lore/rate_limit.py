"""In-memory sliding-window rate limiter per tenant."""

from __future__ import annotations

import os
import threading
import time


class RateLimiter:
    """Simple sliding-window rate limiter keyed by tenant ID."""

    def __init__(
        self,
        max_requests: int | None = None,
        window_seconds: float = 60.0,
    ):
        if max_requests is None:
            max_requests = int(os.environ.get("LORE_RATE_LIMIT_RPM", "100"))
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def allow(self, tenant_id: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            bucket = self._buckets.setdefault(tenant_id, [])
            bucket[:] = [ts for ts in bucket if ts > cutoff]
            if len(bucket) >= self.max_requests:
                return False
            bucket.append(now)
            return True

    @property
    def enabled(self) -> bool:
        return self.max_requests > 0
