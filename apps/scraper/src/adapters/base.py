"""
Base interface for all Fare Source Adapters.

Spec sections:
- §9: Source adapter interface
- §10: Recommended adapter decomposition
"""

import abc
import logging
import time
from typing import Any

from adapters.models import CollectionResult, CollectionStatus, FareSearchRequest

logger = logging.getLogger(__name__)


class FareSourceAdapter(abc.ABC):
    """
    Abstract base class for all scraper adapters.
    
    Spec §9 Responsibilities:
    1. Receive common request
    2. Communicate with source
    3. Obtain raw data
    4. Parse source-specific response
    5. Map source fields to canonical fields
    6. Return observations and collection status
    7. Preserve evidence and diagnostics
    """

    @property
    @abc.abstractmethod
    def adapter_version(self) -> str:
        """Return the version of this adapter (e.g., '1.0.0')."""
        pass

    @property
    @abc.abstractmethod
    def parser_version(self) -> str:
        """Return the version of the parser logic (e.g., '1.0.0')."""
        pass

    async def collect(self, request: FareSearchRequest) -> CollectionResult:
        """
        The main entrypoint for the adapter pipeline.
        This provides a standardized wrapper around the source-specific logic,
        handling timing, error catching, and structured result formatting.
        """
        start_time = time.monotonic()
        http_status = None
        raw_evidence = None
        observations = []
        status = CollectionStatus.UNKNOWN_ERROR
        error_msg = None

        logger.info(f"[{self.__class__.__name__}] Starting collection for {request.origin}->{request.destination} on {request.travel_date}")

        try:
            # 1. Fetch raw data from the source (Client responsibility)
            raw_response, http_status = await self._fetch(request)
            raw_evidence = raw_response
            
            # 2. Parse into observations (Parser & Mapper responsibility)
            if raw_response:
                observations = self._parse(raw_response, request)
                
                if not observations:
                    status = CollectionStatus.NO_RESULTS
                else:
                    status = CollectionStatus.SUCCESS
            else:
                status = CollectionStatus.NO_RESULTS

        except NotImplementedError as e:
            status = CollectionStatus.SOURCE_ERROR
            error_msg = str(e)
            logger.error(f"[{self.__class__.__name__}] NotImplementedError: {e}")
        except Exception as e:
            # Catch-all to ensure we always return a structured CollectionResult
            status = CollectionStatus.SOURCE_ERROR
            error_msg = str(e)
            logger.exception(f"[{self.__class__.__name__}] Unhandled exception during collect: {e}")

        elapsed_ms = int((time.monotonic() - start_time) * 1000)

        return CollectionResult(
            status=status,
            observations=observations,
            request_id=request.request_id,
            http_status=http_status,
            response_time_ms=elapsed_ms,
            # Ideally, raw_evidence should be pushed to S3 and we store the URI here.
            # But for the adapter interface, we pass back the URI if we saved it,
            # or the raw payload if we haven't (depends on how persistence is orchestrated).
            # For now, we mock the URI logic or expect a wrapper to handle large evidence.
            adapter_version=self.adapter_version,
            parser_version=self.parser_version,
            error_message=error_msg,
        )

    @abc.abstractmethod
    async def _fetch(self, request: FareSearchRequest) -> tuple[Any, int | None]:
        """
        Communicate with the source and obtain raw data.
        Returns a tuple of (raw_data, http_status).
        """
        pass

    @abc.abstractmethod
    def _parse(self, raw_data: Any, request: FareSearchRequest) -> list:
        """
        Parse source-specific response and map to canonical fields.
        Returns a list of FareObservation objects.
        """
        pass
