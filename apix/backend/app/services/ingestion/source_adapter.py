"""Source adapter protocol for the ingestion layer.

Defines the interface that all source adapters must implement.
This allows mock adapters (POC) and real adapters (production) to be
used interchangeably without modifying the ingestion pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional, Protocol, runtime_checkable


@dataclass
class RawFareObservation:
    """
    A raw fare observation as returned by a source adapter.
    Mirrors the fare_observations table before quality assessment.
    """
    source_name: str
    airline_code: str
    origin: str
    destination: str
    search_timestamp: datetime
    travel_date: date
    lead_days: int
    fare_class: str
    passenger_count: int
    base_fare: Optional[float]
    taxes: Optional[float]
    airport_charges: Optional[float]
    convenience_fee: Optional[float]
    total_fare: Optional[float]
    currency: str
    availability: str  # available | sold_out | limited
    raw_payload: dict = field(default_factory=dict)


@runtime_checkable
class FareSourceAdapter(Protocol):
    """
    Protocol that all source adapters must implement.

    Future real adapters (IndigoAdapter, AirIndiaAdapter, OTAAdapter)
    will implement this same interface.
    """

    async def collect(
        self,
        origin: str,
        destination: str,
        travel_date: date,
        passengers: int = 1,
        cabin: str = "economy",
    ) -> list[RawFareObservation]:
        """Collect fare observations for a route/date combination."""
        ...

    @property
    def source_name(self) -> str:
        """Human-readable source name."""
        ...

    @property
    def source_type(self) -> str:
        """Source type: airline_direct | ota_mock | ota_live."""
        ...

    @property
    def status(self) -> str:
        """
        Current source status.
        Values: AVAILABLE | RATE_LIMITED | BLOCKED | SOURCE_UNAVAILABLE
        """
        ...
