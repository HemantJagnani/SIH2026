"""
Abstract base class for all fare data sources.

Every source must implement `fetch`, which returns a list of Quote objects
plus a RawSnapshot for audit. The compliance gate must be invoked inside
each concrete source before any HTTP request.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from apix.models import Quote, RawSnapshot


class FareSource(ABC):
    """Interface that every fare data source must satisfy."""

    @abstractmethod
    def fetch(
        self,
        route: str,
        origin: str,
        destination: str,
        travel_date: date,
        run_id: int,
    ) -> tuple[list[Quote], RawSnapshot]:
        """
        Fetch fares for *route* departing on *travel_date*.

        Returns:
            quotes: parsed fare quotes (may be empty on failure/block)
            snapshot: the raw response record (http_status may be None)

        Notes:
            - On a compliance refusal, return ([], snapshot_with_robots_allowed=False).
            - On HTTP 403/429, CAPTCHA or login wall: return a failed snapshot
              with the reason; do not retry with altered behaviour.
            - On a network timeout only: one retry after 60 s is permitted.
        """
        ...
