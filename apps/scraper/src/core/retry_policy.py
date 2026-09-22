"""
retry_policy.py — HTTP Status Policy decision engine for Phase 9.

Phase 9 spec §http-status-policy:
    - 200 + valid → PARSE
    - 403, 401, 451 → STOP (do not retry, do not rotate)
    - 429 → BACKOFF (honor Retry-After)
    - 408, 5xx → RETRY (bounded max 2)

This module replaces generic retry logic with an explicit decision table
that yields one of 4 actions: PARSE, STOP, RETRY, BACKOFF.
"""

from enum import Enum
import logging

logger = logging.getLogger(__name__)

class HttpAction(str, Enum):
    """Actions the orchestrator must take based on HTTP status."""
    PARSE = "PARSE"
    STOP = "STOP"
    RETRY = "RETRY"
    BACKOFF = "BACKOFF"

class HttpStatusPolicy:
    """
    Implements the Phase 9 HTTP status decision table.
    """

    @staticmethod
    def evaluate(status_code: int) -> HttpAction:
        """
        Evaluate an HTTP status code and return the required action.

        Args:
            status_code: The HTTP response status code.

        Returns:
            HttpAction (PARSE, STOP, RETRY, BACKOFF)
        """
        if status_code == 200:
            return HttpAction.PARSE
            
        elif status_code in (401, 403, 451):
            logger.warning(f"HttpStatusPolicy: Hard block detected (HTTP {status_code}) -> STOP")
            return HttpAction.STOP
            
        elif status_code == 429:
            logger.warning("HttpStatusPolicy: Rate limit hit (HTTP 429) -> BACKOFF")
            return HttpAction.BACKOFF
            
        elif status_code == 408 or (500 <= status_code < 600):
            logger.warning(f"HttpStatusPolicy: Transient error (HTTP {status_code}) -> RETRY")
            return HttpAction.RETRY
            
        else:
            # Default for unknown non-200 (e.g. 404, 400) is to STOP
            # as it implies a bad request or missing endpoint, not a transient failure.
            logger.warning(f"HttpStatusPolicy: Unhandled status (HTTP {status_code}) -> STOP")
            return HttpAction.STOP
