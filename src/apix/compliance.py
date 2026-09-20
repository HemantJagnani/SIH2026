"""
Compliance gate for APIx.

Before any HTTP request, this module checks robots.txt for the target URL
using Python's built-in urllib.robotparser. Results are cached per host
for the lifetime of a run.

Every decision (allowed or refused) is logged.
"""
from __future__ import annotations

import logging
import urllib.robotparser
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import ClassVar
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class Decision(Enum):
    ALLOWED = "allowed"
    REFUSED = "refused"


@dataclass(frozen=True)
class Allowed:
    url: str
    decision: Decision = field(default=Decision.ALLOWED, init=False)


@dataclass(frozen=True)
class Refused:
    url: str
    reason: str
    decision: Decision = field(default=Decision.REFUSED, init=False)


# Type alias for a compliance check result
CheckResult = Allowed | Refused


class ComplianceGate:
    """
    Checks robots.txt for each URL before a request is issued.

    Usage::

        gate = ComplianceGate(user_agent="APIx-Prototype/0.1")
        result = gate.check("https://example.com/flights?from=DEL&to=BOM")
        if isinstance(result, Refused):
            logger.warning("Blocked: %s", result.reason)
            return
    """

    _parser_cache: ClassVar[dict[str, urllib.robotparser.RobotFileParser]] = {}

    def __init__(self, user_agent: str) -> None:
        self.user_agent = user_agent
        self._log: list[dict] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check(self, url: str) -> CheckResult:
        """
        Check whether fetching *url* is allowed by the host's robots.txt.

        Returns Allowed or Refused. Logs the decision either way.
        Refused is returned if:
          - robots.txt disallows the path for our UA
          - robots.txt cannot be fetched (conservative refusal)
        """
        try:
            parser = self._get_parser(url)
        except Exception as exc:
            result: CheckResult = Refused(
                url=url,
                reason=f"Could not fetch or parse robots.txt: {exc}",
            )
            self._record(result)
            return result

        if parser.can_fetch(self.user_agent, url):
            result = Allowed(url=url)
        else:
            result = Refused(
                url=url,
                reason="Disallowed by robots.txt",
            )

        self._record(result)
        return result

    def get_log(self) -> list[dict]:
        """Return a copy of all compliance decisions recorded so far."""
        return list(self._log)

    @classmethod
    def clear_cache(cls) -> None:
        """Flush the per-host robots.txt cache (call between runs)."""
        cls._parser_cache.clear()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_parser(self, url: str) -> urllib.robotparser.RobotFileParser:
        parsed = urlparse(url)
        host_key = f"{parsed.scheme}://{parsed.netloc}"

        if host_key not in self._parser_cache:
            robots_url = f"{host_key}/robots.txt"
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(robots_url)
            rp.read()  # may raise on network error
            self.__class__._parser_cache[host_key] = rp
            logger.info("Fetched robots.txt for %s", host_key)

        return self._parser_cache[host_key]

    def _record(self, result: CheckResult) -> None:
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "url": result.url,
            "decision": result.decision.value,
            "reason": getattr(result, "reason", None),
        }
        self._log.append(entry)
        if isinstance(result, Refused):
            logger.warning(
                "COMPLIANCE REFUSED: %s — %s", result.url, result.reason
            )
        else:
            logger.debug("COMPLIANCE ALLOWED: %s", result.url)
