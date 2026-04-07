"""In-memory sliding-window rate limiter per tenant."""

from __future__ import annotations

import os
import threading
import time

from . import env_vars


class RateLimiter:
    """Simple sliding-window rate limiter keyed by tenant ID."""

    def __init__(
        self,
        max_requests: int | None = None,
        window_seconds: float = 60.0,
    ):
        env_vars.require_no_legacy_env_vars()
        if max_requests is None:
            max_requests = int(os.environ.get(env_vars.RATE_LIMIT_RPM, "100"))
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def _prune_locked(self, cutoff: float) -> None:
        for tenant_id, bucket in list(self._buckets.items()):
            bucket[:] = [ts for ts in bucket if ts > cutoff]
            if not bucket:
                del self._buckets[tenant_id]

    def allow(self, tenant_id: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            self._prune_locked(cutoff)
            bucket = self._buckets.setdefault(tenant_id, [])
            if len(bucket) >= self.max_requests:
                return False
            bucket.append(now)
            return True

    @property
    def enabled(self) -> bool:
        return self.max_requests > 0
