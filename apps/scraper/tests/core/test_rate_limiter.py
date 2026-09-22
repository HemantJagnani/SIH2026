"""
Unit tests for RateLimiter and SourceRateLimiter (Milestone 1).

- RateLimiter tests: sync block-state tracker (pre-existing)
- SourceRateLimiter tests: async interval-based pacing (Phase 9 addition)

No network calls are made here.

Run with:
    pytest apps/scraper/tests/core/test_rate_limiter.py -v
"""

import asyncio
import os
import sys
import pytest
from time import monotonic

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

from core.rate_limiter import (
    RateLimiter, RateLimitConfig, SourceBlockedError,
    SourceRateLimiter, SourceRateLimitConfig,
)


def test_rate_limiter_configures_successfully():
    limiter = RateLimiter()
    config = RateLimitConfig(max_concurrency=5, requests_per_minute=30, delay_between_requests_ms=1000)
    
    limiter.configure("indigo", config)
    assert "indigo" in limiter._configs
    assert limiter._configs["indigo"].max_concurrency == 5


def test_rate_limiter_blocks_source():
    limiter = RateLimiter()
    
    assert not limiter.is_blocked("indigo")
    limiter.block_source("indigo", "CAPTCHA detected")
    assert limiter.is_blocked("indigo")


def test_rate_limiter_raises_on_blocked_source():
    limiter = RateLimiter()
    limiter.block_source("indigo", "403 Forbidden")

    with pytest.raises(SourceBlockedError) as exc_info:
        limiter.check_request("indigo")

    assert "blocked" in str(exc_info.value).lower()
    assert "403 Forbidden" in str(exc_info.value)


def test_rate_limiter_allows_unblocked_source():
    limiter = RateLimiter()
    # Should not raise
    limiter.check_request("indigo")


# ---------------------------------------------------------------------------
# SourceRateLimiter — async interval-based pacing (Phase 9)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_source_rate_limiter_first_call_is_immediate() -> None:
    """First wait() on a fresh limiter should not sleep."""
    limiter = SourceRateLimiter(SourceRateLimitConfig(min_interval_seconds=5.0))
    start = monotonic()
    await limiter.wait()
    elapsed = monotonic() - start
    assert elapsed < 0.15, f"First call took {elapsed:.3f}s — expected < 0.15s"


@pytest.mark.asyncio
async def test_source_rate_limiter_second_call_is_delayed() -> None:
    """Second immediate call should sleep for roughly the configured interval."""
    interval = 0.2
    limiter = SourceRateLimiter(SourceRateLimitConfig(min_interval_seconds=interval))
    await limiter.wait()           # First call — immediate
    start = monotonic()
    await limiter.wait()           # Second call — should sleep ~0.2s
    elapsed = monotonic() - start
    assert elapsed >= interval * 0.85, (
        f"Expected ~{interval}s delay; got {elapsed:.3f}s"
    )


@pytest.mark.asyncio
async def test_source_rate_limiter_call_after_interval_is_immediate() -> None:
    """After sleeping past the interval, the next call should be instant."""
    interval = 0.1
    limiter = SourceRateLimiter(SourceRateLimitConfig(min_interval_seconds=interval))
    await limiter.wait()
    await asyncio.sleep(interval + 0.05)
    start = monotonic()
    await limiter.wait()
    elapsed = monotonic() - start
    assert elapsed < 0.15, f"Post-interval call should be immediate; got {elapsed:.3f}s"


def test_source_rate_limiter_default_config() -> None:
    """Default config should have 5s interval and concurrency=1."""
    limiter = SourceRateLimiter()
    assert limiter.min_interval_seconds == 5.0
