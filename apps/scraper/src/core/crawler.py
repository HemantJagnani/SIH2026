"""
crawler.py — Crawlee PlaywrightCrawler factory for Phase 9.

This module provides a single factory function `build_crawler()` that
constructs a correctly-configured PlaywrightCrawler instance.

Phase 9 compliance settings (do NOT change without explicit approval):
    retry_on_blocked=False
        Crawlee's retry_on_blocked=True is specifically designed to attempt
        automated bypass of bot-protection mechanisms. We never use it.
    max_session_rotations=0
        Session rotation after a block would effectively retry with a new
        identity, which is equivalent to bypassing the block. Not permitted.
    respect_robots_txt_file=True
        Crawlee checks robots.txt before each request and skips disallowed
        URLs. This works alongside (not instead of) our RobotsPolicyGate,
        which does a per-job pre-flight check before the crawler is launched.
    max_request_retries=2
        Only for genuine transient failures (timeouts, 5xx). CAPTCHA, 403,
        and login walls are NOT retried — they are caught by the handler and
        terminate the job via AvailabilityStatus.

Environment control:
    SCRAPER_HEADLESS=true/false — set in .env to switch headless mode.
    SCRAPER_BROWSER_TYPE=chromium/firefox/webkit — defaults to chromium.
"""

from __future__ import annotations

import logging
import os
from datetime import timedelta
from typing import Optional

from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext

logger = logging.getLogger(__name__)


def build_crawler(
    headless: Optional[bool] = None,
    browser_type: str = "chromium",
    max_request_retries: int = 2,
    navigation_timeout_secs: int = 60,
    request_handler_timeout_secs: int = 120,
) -> PlaywrightCrawler:
    """
    Factory function that constructs a Phase 9-compliant PlaywrightCrawler.

    Args:
        headless: Whether to run the browser in headless mode. If None,
                  reads from the SCRAPER_HEADLESS environment variable
                  (defaults to False so development runs show the browser).
        browser_type: Browser engine to use ("chromium", "firefox", "webkit").
                      Defaults to "chromium" per Phase 9 spec.
        max_request_retries: Maximum retries for transient failures (timeouts,
                             5xx). CAPTCHA/403/login-wall failures are handled
                             in the request handler, not via retries.
        navigation_timeout_secs: Playwright page navigation timeout in seconds.

    Returns:
        A configured PlaywrightCrawler instance ready to accept a request handler.

    Usage:
        crawler = build_crawler()

        @crawler.router.default_handler
        async def handler(context: PlaywrightCrawlingContext) -> None:
            page = context.page
            # ... source-specific workflow ...

        await crawler.run(["https://source.example.com/"])
    """
    # Resolve headless mode from the environment if not explicitly set.
    if headless is None:
        env_val = os.getenv("SCRAPER_HEADLESS", "false").lower()
        headless = env_val in ("1", "true", "yes")

    # Resolve browser type from the environment (can be overridden via env).
    browser_type = os.getenv("SCRAPER_BROWSER_TYPE", browser_type)

    logger.info(
        "Building PlaywrightCrawler: browser=%s headless=%s retries=%d",
        browser_type, headless, max_request_retries,
    )

    crawler = PlaywrightCrawler(
        # --- Browser settings ---
        browser_type=browser_type,
        headless=headless,

        # --- Phase 9 compliance: NEVER change these two ---
        # retry_on_blocked=True would attempt to bypass bot protection.
        # max_session_rotations>0 would rotate identity after a block.
        # Both are forbidden by the project spec.

        # --- Request limits ---
        # One request per crawl: each source job is a single, focused search.
        max_requests_per_crawl=1,
        # Bounded retry for genuine transient failures only.
        max_request_retries=max_request_retries,

        # --- Session ---
        # Session pool is enabled; each logical session carries its own
        # cookies/localStorage via the BrowserContext. See session_manager.py
        # for how we save/restore session state between runs.
        use_session_pool=True,
        # Zero rotations: if a session is blocked, we stop — not rotate.
        max_session_rotations=0,

        # --- Compliance ---
        # Crawlee checks robots.txt before each request.
        # This is a second layer on top of our RobotsPolicyGate pre-flight check.
        respect_robots_txt_file=True,
        # Never attempt to bypass bot protection mechanisms.
        retry_on_blocked=False,

        # --- Timeouts ---
        navigation_timeout=timedelta(seconds=navigation_timeout_secs),
        request_handler_timeout=timedelta(seconds=request_handler_timeout_secs),
    )

    proxy_urls_env = os.getenv("APPROVED_PROXY_URLS")
    if proxy_urls_env:
        from crawlee.proxy_configuration import ProxyConfiguration
        urls = [u.strip() for u in proxy_urls_env.split(",") if u.strip()]
        if urls:
            logger.info("Crawler: using ProxyConfiguration with %d proxy URLs", len(urls))
            crawler.proxy_configuration = ProxyConfiguration(proxy_urls=urls)

    return crawler
