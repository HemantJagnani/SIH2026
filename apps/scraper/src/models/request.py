"""
FareSearchRequest — the common collection request model.

Every API adapter and web adapter must accept exactly this request object.
No adapter should define its own request format.

Source: spec §6, §7, §8, §44 Phase 1.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from pydantic import BaseModel, Field, UUID4, field_validator, model_validator

from .enums import CabinClass, CollectionMode, TripType


# ---------------------------------------------------------------------------
# Passenger count sub-model
# Defined as a nested model so passenger fields are grouped and validated
# together as a unit.
# ---------------------------------------------------------------------------

class PassengerCount(BaseModel):
    """
    Number of passengers per category.
    Source: spec §6.
    Defaults match the project POC defaults: 1 adult, no children or infants.
    """
    adults: Annotated[int, Field(ge=1, description="Number of adult passengers")] = 1
    children: Annotated[int, Field(ge=0, description="Number of child passengers")] = 0
    infants: Annotated[int, Field(ge=0, description="Number of infant passengers")] = 0

    @model_validator(mode="after")
    def total_must_be_positive(self) -> "PassengerCount":
        if self.adults + self.children + self.infants < 1:
            raise ValueError("Total passenger count must be at least 1.")
        return self


# ---------------------------------------------------------------------------
# FareSearchRequest
# ---------------------------------------------------------------------------

class FareSearchRequest(BaseModel):
    """
    The single, unified request object passed to every source adapter.

    All fields map directly to the canonical request defined in spec §6.
    Adapters must translate this into whatever the source API or webpage expects.

    Defaults (from spec §6):
        adults=1, children=0, infants=0,
        cabin=ECONOMY, trip_type=ONE_WAY, currency=INR

    The request_id is auto-generated as a UUID4 if not supplied,
    providing a stable correlation key between the request and the
    raw evidence stored in object storage.
    """

    # --- Identity & Correlation ---
    request_id: UUID4 = Field(
        default_factory=uuid.uuid4,
        description="Unique identifier for this search request; links to raw evidence.",
    )

    # --- Source ---
    source: str = Field(
        ...,
        description="Source identifier (e.g. 'indigo', 'cleartrip'). Must match sources.yaml.",
    )

    # --- Route ---
    origin: str = Field(
        ...,
        min_length=3,
        max_length=3,
        description="Departure airport IATA code (e.g. 'DEL').",
    )
    destination: str = Field(
        ...,
        min_length=3,
        max_length=3,
        description="Arrival airport IATA code (e.g. 'BOM').",
    )

    # --- Date ---
    travel_date: date = Field(
        ...,
        description="Intended flight date (YYYY-MM-DD). Computed as collection_date + lead_days.",
    )
    lead_days: int = Field(
        ...,
        ge=0,
        description="Number of days between collection date and travel date (T+N).",
    )

    # --- Itinerary ---
    trip_type: TripType = Field(
        default=TripType.ONE_WAY,
        description="ONE_WAY or ROUND_TRIP. Default is ONE_WAY per spec §6.",
    )
    cabin: CabinClass = Field(
        default=CabinClass.ECONOMY,
        description="Cabin class. Default is ECONOMY per spec §6.",
    )
    passenger_count: PassengerCount = Field(
        default_factory=PassengerCount,
        description="Breakdown of passenger count by category.",
    )

    # --- Currency ---
    currency: str = Field(
        default="INR",
        description="Currency code. Must be 'INR' for this project.",
    )

    # --- Collection ---
    collection_mode: CollectionMode = Field(
        ...,
        description="How data will be collected: API, HTTP, or BROWSER.",
    )

    # ---------------------------------------------------------------------------
    # Validators
    # ---------------------------------------------------------------------------

    @field_validator("origin", "destination", mode="before")
    @classmethod
    def uppercase_iata(cls, v: str) -> str:
        """IATA codes must be uppercase."""
        return v.strip().upper()

    @field_validator("currency", mode="before")
    @classmethod
    def uppercase_currency(cls, v: str) -> str:
        return v.strip().upper()

    @model_validator(mode="after")
    def origin_not_equal_to_destination(self) -> "FareSearchRequest":
        """Route must have distinct origin and destination. Spec §20."""
        if self.origin == self.destination:
            raise ValueError(
                f"origin and destination must differ; got '{self.origin}' for both."
            )
        return self

    @model_validator(mode="after")
    def currency_must_be_inr(self) -> "FareSearchRequest":
        """Project targets INR only. Spec §6."""
        if self.currency != "INR":
            raise ValueError(
                f"Currency must be 'INR' for this project; got '{self.currency}'."
            )
        return self

    model_config = {"frozen": True}
