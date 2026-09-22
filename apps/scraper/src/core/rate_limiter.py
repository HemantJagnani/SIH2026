"""
Rate limiter for the web collection framework.

Spec §27–29:
- Per-source configurable (max_concurrency, requests_per_minute)
- Stop job (no bypass) on CAPTCHA, 403, or bot challenge.
- Never use IP rotation as evasion.

Phase 9 addition:
- SourceRateLimiter: async token-based limiter that enforces a minimum
  interval between requests to a single source. Works within the asyncio
  event loop used by Crawlee/Playwright, so it does not block the thread.
- Default: 5s minimum interval, max_concurrency=1. These are configured
  per-source in config/sources.yaml and can be adjusted after testing.
- Note: Crawlee has its own internal pacing/concurrency mechanisms. This
  limiter adds a project-level enforcement layer on top, ensuring we
  never go faster than our per-source YAML config allows — even if Crawlee
  itself would permit it.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from time import monotonic
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class SourceBlockedError(Exception):
    """
    Raised when a source is blocked due to CAPTCHA, 403, or bot challenge.
    Spec §29: Never bypass access-control challenges.
    """
    def __init__(self, source: str, reason: str):
        self.source = source
        self.reason = reason
        super().__init__(f"Source '{source}' is blocked: {reason}")


@dataclass
class RateLimitConfig:
    max_concurrency: int
    requests_per_minute: int
    delay_between_requests_ms: int


class RateLimiter:
    """
    Sync tracker for per-source block states across the pipeline.
    Used by the monitoring and retry layers to check whether a source
    has been permanently blocked (e.g. by CAPTCHA or 403) in this run.
    """

    def __init__(self):
        # In a real distributed system, this would be backed by Redis.
        # For now, we store state in memory per worker.
        self._configs: Dict[str, RateLimitConfig] = {}
        self._blocked_sources: Dict[str, str] = {}  # source -> reason

    def configure(self, source: str, config: RateLimitConfig) -> None:
        """Set the rate limit configuration for a specific source."""
        self._configs[source] = config
        logger.info(f"Configured rate limit for {source}: {config}")

    def is_blocked(self, source: str) -> bool:
        """Check if a source is currently blocked due to access restrictions."""
        return source in self._blocked_sources

    def block_source(self, source: str, reason: str) -> None:
        """
        Record an access restriction (CAPTCHA, 403, bot challenge) and block further requests.
        Spec §29: Never bypass.
        """
        self._blocked_sources[source] = reason
        logger.critical(f"Source {source} is now BLOCKED. Reason: {reason}")

    def check_request(self, source: str) -> None:
        """
        Verify if a request can be made to the source.
        Raises SourceBlockedError if the source is blocked.
        """
        if self.is_blocked(source):
            reason = self._blocked_sources[source]
            raise SourceBlockedError(source, reason)

        # Rate limiting logic (delay/concurrency checks) would go here.
        # For the skeleton, we just ensure it's not blocked.
        pass

    def check(self, source: str) -> None:
        """Alias for check_request — preferred in monitoring/refetch code."""
        self.check_request(source)


# ---------------------------------------------------------------------------
# Phase 9 — Async per-source rate limiter
# ---------------------------------------------------------------------------

@dataclass
class SourceRateLimitConfig:
    """
    Per-source rate limit settings, loaded from config/sources.yaml.

    Fields:
        min_interval_seconds: Minimum wait time between requests to this source.
            Default: 5.0s. Adjust per-source only after testing; never set below 3s.
        max_concurrency: Maximum simultaneous requests to this source.
            Default: 1. For a compliant POC, keep this at 1.
    """
    min_interval_seconds: float = 5.0
    max_concurrency: int = 1


class SourceRateLimiter:
    """
    Async rate limiter that enforces a minimum interval between requests
    to a single source, running within the asyncio event loop.

    Phase 9 spec §rate-limiter pattern:

        async def wait(self):
            now = monotonic()
            if now < self.next_allowed_at:
                await asyncio.sleep(self.next_allowed_at - now)
            self.next_allowed_at = monotonic() + self.min_interval

    Usage:
        limiter = SourceRateLimiter(SourceRateLimitConfig(min_interval_seconds=5))
        await limiter.wait()
        # safe to make a request now

    Design note:
        This limiter is intentionally simple. Crawlee provides its own
        concurrency/request-rate controls. This class enforces our project-level
        floor on top, so config/sources.yaml remains the single source of truth
        for how aggressively we hit each source.
    """

    def __init__(self, config: Optional[SourceRateLimitConfig] = None) -> None:
        self._config = config or SourceRateLimitConfig()
        # Timestamp (monotonic) at which the next request is permitted.
        self._next_allowed_at: float = 0.0
        # Semaphore enforces max_concurrency.
        self._semaphore = asyncio.Semaphore(self._config.max_concurrency)

    @property
    def min_interval_seconds(self) -> float:
        return self._config.min_interval_seconds

    async def wait(self) -> None:
        """
        Block (sleep) until the minimum inter-request interval has elapsed,
        then record the next allowed request time.

        This must be called immediately before every outbound request. It is
        safe to call concurrently; the semaphore ensures max_concurrency is
        respected, and the interval guard ensures requests are spaced out.
        """
        async with self._semaphore:
            now = monotonic()
            if now < self._next_allowed_at:
                sleep_for = self._next_allowed_at - now
                logger.debug(
                    "SourceRateLimiter: waiting %.2fs before next request.", sleep_for
                )
                await asyncio.sleep(sleep_for)
            # Update next_allowed_at *after* waking up, using current monotonic time.
            self._next_allowed_at = monotonic() + self._config.min_interval_seconds

