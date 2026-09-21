"""
Crawler Manager for the web collection framework.

Spec §27–28:
- Integrates Crawlee for Python
- HTTP Crawler for structured data
- Playwright Crawler for JS websites
"""

import logging
from typing import Dict, Any, Type

# We use placeholders for Crawlee as we might not have it installed in this environment yet,
# but we design the architecture around it.
try:
    from crawlee.crawlers import PlaywrightCrawler, HttpCrawler
except ImportError:
    # Dummy classes for typing if Crawlee isn't installed in the current environment
    class PlaywrightCrawler: pass
    class HttpCrawler: pass

from adapters.base import FareSourceAdapter
from core.rate_limiter import RateLimiter
from core.retry_policy import RetryPolicy

logger = logging.getLogger(__name__)


class CrawlerManager:
    """
    Manages the lifecycle of scraping jobs, routing them to the correct
    crawler (HTTP vs Playwright) and enforcing rate limits and retries.
    """
    
    def __init__(self, rate_limiter: RateLimiter):
        self.rate_limiter = rate_limiter
        self.retry_policy = RetryPolicy()
        
        # In a full implementation, we'd initialize the actual Crawlee instances here
        self._http_crawler = HttpCrawler()
        self._playwright_crawler = PlaywrightCrawler()
        
        # Registry of adapters to route requests to
        self._adapters: Dict[str, FareSourceAdapter] = {}

    def register_adapter(self, source: str, adapter: FareSourceAdapter) -> None:
        """Register an adapter for a specific source."""
        self._adapters[source] = adapter
        logger.info(f"Registered adapter for source: {source}")

    async def execute_job(self, source: str, request: Any) -> Any:
        """
        Execute a collection job for a given source and request.
        Applies rate limiting and retry policies.
        """
        if source not in self._adapters:
            raise ValueError(f"No adapter registered for source: {source}")

        adapter = self._adapters[source]

        # 1. Check Rate Limiter (will raise PermissionError if blocked)
        self.rate_limiter.check_request(source)

        # 2. Execute via adapter with Retry Policy
        # The adapter itself knows whether to use HTTP or Playwright via its internal implementation,
        # but the CrawlerManager orchestrates the execution envelope.
        
        async def _run_adapter():
            return await adapter.collect(request)

        try:
            # We don't inspect HTTP status here because the adapter encapsulates it in CollectionResult,
            # but for true transient failures, the adapter's `_fetch` might raise exceptions that we catch here.
            result = await self.retry_policy.execute(_run_adapter)
            return result
        except PermissionError as e:
             # If an adapter raises a PermissionError during execution (e.g. hits a CAPTCHA),
             # we must block the source in the rate limiter.
             self.rate_limiter.block_source(source, str(e))
             raise
        except Exception as e:
            logger.error(f"Job execution failed for {source}: {e}")
            raise
