"""
Rate limiter for the web collection framework.

Spec §27–29:
- Per-source configurable (max_concurrency, requests_per_minute)
- Stop job (no bypass) on CAPTCHA, 403, or bot challenge.
- Never use IP rotation as evasion.
"""

import logging
from typing import Optional
from dataclasses import dataclass
from typing import Dict

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
