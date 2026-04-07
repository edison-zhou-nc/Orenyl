"""Tests for in-memory rate limiter."""

from __future__ import annotations

import time

import pytest

from orenyl.rate_limit import RateLimiter


def test_rate_limiter_allows_within_limit():
    limiter = RateLimiter(max_requests=5, window_seconds=60)
    for _ in range(5):
        assert limiter.allow("tenant-a") is True


def test_rate_limiter_blocks_over_limit():
    limiter = RateLimiter(max_requests=3, window_seconds=60)
    for _ in range(3):
        assert limiter.allow("tenant-a") is True
    assert limiter.allow("tenant-a") is False


def test_rate_limiter_isolates_tenants():
    limiter = RateLimiter(max_requests=2, window_seconds=60)
    assert limiter.allow("tenant-a") is True
    assert limiter.allow("tenant-a") is True
    assert limiter.allow("tenant-a") is False
    assert limiter.allow("tenant-b") is True


def test_rate_limiter_resets_after_window():
    limiter = RateLimiter(max_requests=1, window_seconds=0.1)
    assert limiter.allow("tenant-a") is True
    assert limiter.allow("tenant-a") is False
    time.sleep(0.15)
    assert limiter.allow("tenant-a") is True


def test_rate_limiter_prunes_stale_tenant_buckets():
    limiter = RateLimiter(max_requests=1, window_seconds=0.05)

    assert limiter.allow("tenant-a") is True
    time.sleep(0.08)
    assert limiter.allow("tenant-b") is True

    assert "tenant-a" not in limiter._buckets


def test_rate_limiter_rejects_legacy_env_vars(monkeypatch):
    with monkeypatch.context() as m:
        m.setenv("LORE_RATE_LIMIT_RPM", "25")

        with pytest.raises(RuntimeError, match="LORE_RATE_LIMIT_RPM"):
            RateLimiter()
