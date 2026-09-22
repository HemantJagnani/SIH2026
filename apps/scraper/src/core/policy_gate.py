"""
RobotsPolicyGate — robots.txt compliance check before any web request.

Phase 9 spec §robots-policy:
    - respect_robots_txt_file=True is set in the Crawlee crawler.
    - This gate provides an *additional* pre-flight check at the job level,
      before the crawler is even launched for a given source URL.
    - It caches parsed robots.txt content per domain to avoid repeated fetches.
    - It supports a local fixture file path for unit testing, so Milestone 1
      tests do NOT make real network requests.

Usage (production):
    gate = RobotsPolicyGate()
    allowed, reason = await gate.check("https://www.goair.in/search")
    if not allowed:
        # record AvailabilityStatus.ROBOTS_DISALLOWED and stop

Usage (tests):
    gate = RobotsPolicyGate(fixture_path="tests/fixtures/robots_test.txt")
    allowed, reason = await gate.check("https://example.com/search")
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

logger = logging.getLogger(__name__)

# The user-agent string we announce to robots.txt parsers.
# Keeps us honest: we are an automated research tool, not a browser.
ROBOTS_USER_AGENT = "AirfareIndexBot/1.0"


class RobotsPolicyGate:
    """
    Pre-flight policy check: is the target URL permitted by the source's robots.txt?

    Design:
    - Parsed robots.txt entries are cached in memory for the lifetime of this
      object (one per run). This is intentional: we do not want to hammer
      robots.txt endpoints.
    - A fixture_path can be supplied for testing. When set, ALL domains resolve
      to that local file instead of fetching the real robots.txt. This allows
      Milestone 1 unit tests to run fully offline.

    Phase 9 compliance rules enforced here:
    - If robots.txt disallows the path → return (False, ROBOTS_DISALLOWED).
    - If robots.txt cannot be fetched (network error) → log a warning and
      conservatively ALLOW (fail-open), since we cannot confirm a restriction.
    - This gate never retries a disallowed URL.
    """

    def __init__(self, fixture_path: Optional[str | Path] = None) -> None:
        """
        Args:
            fixture_path: Optional path to a local robots.txt fixture file.
                          When provided, this file is used for all domains —
                          intended for offline unit tests only.
        """
        self._fixture_path: Optional[Path] = (
            Path(fixture_path) if fixture_path else None
        )
        # Cache: domain → RobotFileParser instance
        self._cache: dict[str, RobotFileParser] = {}

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def check(self, url: str) -> tuple[bool, str]:
        """
        Check whether the given URL is permitted by the source's robots.txt.

        Returns:
            (True, "allowed") if the URL is permitted.
            (False, reason_string) if it is disallowed.

        This method is async to match the Crawlee/asyncio execution context,
        even though the underlying RobotFileParser is synchronous. The actual
        HTTP fetch is done via httpx in a synchronous call wrapped here.
        """
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        robots_url = f"{domain}/robots.txt"

        parser = await self._get_parser(domain, robots_url)

        # Ask the parser whether our bot is allowed to fetch this path.
        path = parsed.path or "/"
        allowed = parser.can_fetch(ROBOTS_USER_AGENT, path)

        if allowed:
            logger.debug("robots.txt: ALLOWED %s for %s", path, domain)
            return True, "allowed"
        else:
            reason = (
                f"robots.txt at {robots_url} disallows "
                f"'{ROBOTS_USER_AGENT}' from '{path}'"
            )
            logger.warning("robots.txt: DISALLOWED — %s", reason)
            return False, reason

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_parser(self, domain: str, robots_url: str) -> RobotFileParser:
        """Return a cached (or freshly loaded) RobotFileParser for the domain."""
        if domain in self._cache:
            return self._cache[domain]

        parser = RobotFileParser()

        if self._fixture_path is not None:
            # Offline / test mode: load from a local file instead of fetching.
            logger.debug("PolicyGate: using fixture %s for %s", self._fixture_path, domain)
            content = Path(self._fixture_path).read_text(encoding="utf-8")
            parser.parse(content.splitlines())
        else:
            # Production mode: fetch robots.txt from the real domain.
            content = await self._fetch_robots_txt(robots_url)
            if content is not None:
                parser.parse(content.splitlines())
            else:
                # Network failure — fail-open with a warning.
                # We cannot confirm a restriction, so we allow but log it.
                logger.warning(
                    "PolicyGate: could not fetch robots.txt from %s; "
                    "proceeding with no restrictions (fail-open). "
                    "This is conservative — retry manually before assuming access is allowed.",
                    robots_url,
                )
                # An empty parser allows everything by default.

        self._cache[domain] = parser
        return parser

    async def _fetch_robots_txt(self, robots_url: str) -> Optional[str]:
        """
        Fetch the robots.txt content from the given URL.

        Returns the text content on success, None on any network/HTTP failure.
        We use a short timeout; robots.txt is a small, fast resource.
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(robots_url, follow_redirects=True)
            if response.status_code == 200:
                return response.text
            elif response.status_code == 404:
                # No robots.txt means no restrictions — standard interpretation.
                logger.debug("PolicyGate: no robots.txt at %s (404) — unrestricted.", robots_url)
                return ""
            else:
                logger.warning(
                    "PolicyGate: unexpected HTTP %d from %s — fail-open.",
                    response.status_code, robots_url,
                )
                return None
        except httpx.RequestError as exc:
            logger.warning("PolicyGate: network error fetching %s — %s", robots_url, exc)
            return None
