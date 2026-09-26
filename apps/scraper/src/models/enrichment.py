"""
Enrichment models and queue tasks.

Source: Phase 5, Phase 6 specs.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field, UUID4


class EnrichmentType(str, Enum):
    """Types of enrichment that can be performed on an observation."""
    FLIGHT_DETAILS = "FLIGHT_DETAILS"
    FARE_OPTIONS = "FARE_OPTIONS"
    FARE_BREAKDOWN = "FARE_BREAKDOWN"
    BAGGAGE = "BAGGAGE"
    FARE_RULES = "FARE_RULES"
    BOOKING_OPTIONS = "BOOKING_OPTIONS"


class EnrichmentStatus(str, Enum):
    """Status of an enrichment task."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    SKIPPED = "SKIPPED"


MAX_ENRICHMENT_ATTEMPTS = 2


class EnrichmentTask(BaseModel):
    """
    Unit of work queued for enriching an itinerary or fare observation.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    task_id: UUID4 = Field(default_factory=uuid.uuid4)
    observation_id: str = Field(..., description="ID of the observation being enriched.")
    source: str = Field(..., description="Source portal ID (e.g. 'google_flights', 'easemytrip').")
    enrichment_type: EnrichmentType = Field(..., description="Target enrichment data.")
    priority: int = Field(default=1, ge=1, le=10, description="Higher priority executes earlier.")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    attempts: int = Field(default=0, ge=0)
    max_attempts: int = Field(default=MAX_ENRICHMENT_ATTEMPTS, ge=1)
    status: EnrichmentStatus = Field(default=EnrichmentStatus.PENDING)
    failure_reason: Optional[str] = Field(default=None)
    context_data: dict[str, Any] = Field(default_factory=dict, description="Metadata or DOM locator context.")

    def can_retry(self) -> bool:
        return self.attempts < self.max_attempts and self.status not in (
            EnrichmentStatus.SUCCESS,
            EnrichmentStatus.BLOCKED,
            EnrichmentStatus.SKIPPED,
        )

    def mark_running(self) -> None:
        self.attempts += 1
        self.status = EnrichmentStatus.RUNNING

    def mark_success(self) -> None:
        self.status = EnrichmentStatus.SUCCESS

    def mark_partial(self, reason: Optional[str] = None) -> None:
        self.status = EnrichmentStatus.PARTIAL
        self.failure_reason = reason

    def mark_failed(self, reason: str) -> None:
        self.failure_reason = reason
        self.status = EnrichmentStatus.FAILED

    def mark_blocked(self, reason: str) -> None:
        self.failure_reason = reason
        self.status = EnrichmentStatus.BLOCKED

    def mark_skipped(self, reason: str) -> None:
        self.failure_reason = reason
        self.status = EnrichmentStatus.SKIPPED


class EnrichmentPolicy(BaseModel):
    """
    Policy controlling sample selection for deep enrichment (Phase 6).
    Never enriches 100% of flights; selects a statistically balanced sample.
    """
    max_samples_per_search: int = Field(default=5, ge=1, description="Maximum flights to enrich per route/date search.")
    max_per_airline: int = Field(default=2, ge=1, description="Max flights per airline in sample.")
    include_nonstop: bool = True
    include_one_stop: bool = True
    price_band_distribution: dict[str, int] = Field(
        default_factory=lambda: {"LOW": 2, "MID": 2, "HIGH": 1}
    )

    def select_sample(self, observations: list[Any]) -> list[Any]:
        """
        Select representative observations stratified by airline, stops, and price range.
        Does NOT alter weights or average rows directly.
        """
        if not observations or self.max_samples_per_search <= 0:
            return []

        # Sort by total_fare
        sorted_obs = sorted(
            [o for o in observations if getattr(o, "total_fare", None) is not None],
            key=lambda x: float(x.total_fare),
        )
        if not sorted_obs:
            return observations[:self.max_samples_per_search]

        n = len(sorted_obs)
        if n <= self.max_samples_per_search:
            return list(sorted_obs)

        # Partition into price bands: LOW (first 33%), MID (middle 33%), HIGH (top 33%)
        low_band = sorted_obs[: n // 3]
        mid_band = sorted_obs[n // 3 : 2 * (n // 3)]
        high_band = sorted_obs[2 * (n // 3) :]

        selected = []
        airline_counts: dict[str, int] = {}

        def try_pick(candidates: list[Any], max_count: int):
            picked = 0
            for item in candidates:
                if picked >= max_count:
                    break
                al = getattr(item, "airline", "UNKNOWN")
                if airline_counts.get(al, 0) < self.max_per_airline and item not in selected:
                    selected.append(item)
                    airline_counts[al] = airline_counts.get(al, 0) + 1
                    picked += 1

        try_pick(low_band, self.price_band_distribution.get("LOW", 2))
        try_pick(mid_band, self.price_band_distribution.get("MID", 2))
        try_pick(high_band, self.price_band_distribution.get("HIGH", 1))

        # If not enough picked due to airline caps, fill remaining from any available
        if len(selected) < self.max_samples_per_search:
            for item in sorted_obs:
                if len(selected) >= self.max_samples_per_search:
                    break
                if item not in selected:
                    selected.append(item)

        return selected
