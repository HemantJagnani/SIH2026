"""
Itinerary and FareOffer models.

Explicit separation between:
A. Itinerary (flight schedule, route, airline, stops, segments)
B. Fare Offer (commercial pricing, fare family, rules, baggage, taxes)

Source: Phase 2, Phase 3 specs.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, Field, UUID4, field_validator

from .enums import AvailabilityStatus, CabinClass, TripType
from .provenance import FieldProvenance, FieldStatus, MissingReason


class FlightSegment(BaseModel):
    """
    Represents a single segment of a multi-leg or direct itinerary.
    """
    segment_number: int = Field(..., ge=1, description="Sequential index of the segment (1-based).")
    origin: str = Field(..., min_length=3, max_length=3, description="Departure airport IATA code.")
    destination: str = Field(..., min_length=3, max_length=3, description="Arrival airport IATA code.")
    marketing_carrier: Optional[str] = Field(default=None, description="Marketing airline code or name.")
    operating_carrier: Optional[str] = Field(default=None, description="Operating airline code or name.")
    flight_number: Optional[str] = Field(default=None, description="Flight number for this segment (e.g. '6E-512').")
    departure_time: Optional[datetime] = Field(default=None, description="Scheduled departure datetime.")
    arrival_time: Optional[datetime] = Field(default=None, description="Scheduled arrival datetime.")
    duration_minutes: Optional[int] = Field(default=None, ge=0, description="Duration in minutes.")
    aircraft_type: Optional[str] = Field(default=None, description="Aircraft type equipment (e.g. 'A320neo').")
    cabin_class: Optional[CabinClass] = Field(default=None, description="Cabin class for this segment.")

    @field_validator("origin", "destination", mode="before")
    @classmethod
    def uppercase_iata(cls, v: str) -> str:
        return v.strip().upper() if isinstance(v, str) else v


class Itinerary(BaseModel):
    """
    Represents the operational flight schedule (independent of specific fare offers).
    """
    itinerary_id: UUID4 = Field(default_factory=uuid.uuid4, description="Unique ID for this itinerary.")
    origin: str = Field(..., min_length=3, max_length=3, description="Origin airport IATA code.")
    destination: str = Field(..., min_length=3, max_length=3, description="Destination airport IATA code.")
    travel_date: date = Field(..., description="Date of departure (YYYY-MM-DD).")
    airline: str = Field(..., description="Primary airline name or marketing carrier.")
    airline_code: Optional[str] = Field(default=None, description="Airline IATA code (e.g. '6E').")
    flight_number: Optional[str] = Field(default=None, description="Flight number as exposed (e.g. '6E-205').")
    departure_time: Optional[datetime] = Field(default=None, description="Departure datetime.")
    arrival_time: Optional[datetime] = Field(default=None, description="Arrival datetime.")
    duration_minutes: Optional[int] = Field(default=None, ge=0, description="Flight duration in minutes.")
    stops: int = Field(default=0, ge=0, description="Number of stops (0 = non-stop).")
    trip_type: TripType = Field(default=TripType.ONE_WAY, description="Trip type.")
    
    # CRITICAL: Always use Field(default_factory=list), NEVER mutable default []
    flight_segments: list[FlightSegment] = Field(default_factory=list, description="List of individual flight segments.")

    @field_validator("origin", "destination", mode="before")
    @classmethod
    def uppercase_iata(cls, v: str) -> str:
        return v.strip().upper() if isinstance(v, str) else v


class PriceStatus(str):
    """Price semantics for displayed fares."""
    DISPLAYED_TOTAL = "DISPLAYED_TOTAL"
    DISPLAYED_FROM = "DISPLAYED_FROM"
    DISPLAYED_FARE = "DISPLAYED_FARE"
    PRICE_CHANGED = "PRICE_CHANGED"
    UNAVAILABLE = "UNAVAILABLE"
    SOLD_OUT = "SOLD_OUT"
    UNKNOWN = "UNKNOWN"


class FareOffer(BaseModel):
    """
    Represents a specific commercial pricing offer for an Itinerary.
    One itinerary may have multiple fare offers (e.g. Basic, Standard, Flex).
    """
    offer_id: UUID4 = Field(default_factory=uuid.uuid4, description="Unique offer identifier.")
    itinerary_id: UUID4 = Field(..., description="References the parent Itinerary.")
    source: str = Field(..., description="Source portal ID (e.g. 'google_flights', 'easemytrip').")
    booking_source: Optional[str] = Field(default=None, description="Provider/OTA fulfilling booking if known.")
    
    # Classification
    fare_family: Optional[str] = Field(default=None, description="Fare family name (e.g. 'SAVER', 'FLEXI').")
    fare_class: Optional[str] = Field(default=None, description="RBD / booking class (e.g. 'Q', 'Y').")
    cabin_class: CabinClass = Field(default=CabinClass.ECONOMY, description="Cabin class of offer.")
    
    # Baggage information
    cabin_baggage_kg: Optional[int] = Field(default=None, ge=0, description="Cabin baggage allowance in kg.")
    checkin_baggage_kg: Optional[int] = Field(default=None, ge=0, description="Check-in baggage allowance in kg.")
    baggage_information: Optional[str] = Field(default=None, description="Raw baggage description.")
    
    # Refundability / Changeability
    refund_status: Optional[str] = Field(default=None, description="REFUNDABLE, NON_REFUNDABLE, or UNKNOWN.")
    cancellation_fee: Optional[Decimal] = Field(default=None, ge=0, description="Fee to cancel flight.")
    change_fee: Optional[Decimal] = Field(default=None, ge=0, description="Fee to change flight.")
    changeability_status: Optional[str] = Field(default=None, description="CHANGEABLE or NON_CHANGEABLE.")
    
    # Price breakdown components (strictly NULL if not exposed by source)
    base_fare: Optional[Decimal] = Field(default=None, ge=0, description="Base fare if explicitly exposed.")
    taxes: Optional[Decimal] = Field(default=None, ge=0, description="Taxes if explicitly exposed.")
    airport_charges: Optional[Decimal] = Field(default=None, ge=0, description="Airport charges if exposed.")
    security_fee: Optional[Decimal] = Field(default=None, ge=0, description="Security fees if exposed.")
    gst: Optional[Decimal] = Field(default=None, ge=0, description="GST / tax component if exposed.")
    convenience_fee: Optional[Decimal] = Field(default=None, ge=0, description="Convenience fee if exposed.")
    discount: Optional[Decimal] = Field(default=None, ge=0, description="Discount if exposed.")
    
    # Total consumer payable fare (Target price concept)
    total_fare: Decimal = Field(..., ge=0, description="Total consumer payable price.")
    currency: str = Field(default="INR", description="ISO currency code (INR).")
    
    # Statuses
    price_status: str = Field(default=PriceStatus.DISPLAYED_TOTAL, description="Price semantics.")
    availability_status: AvailabilityStatus = Field(default=AvailabilityStatus.AVAILABLE)
    inventory_status: Optional[str] = Field(default=None, description="e.g. 'few_seats_left'.")
    seats_remaining_displayed: Optional[int] = Field(default=None, ge=0)
    
    # Field provenance tracking
    provenance: dict[str, FieldProvenance] = Field(default_factory=dict, description="Metadata explaining field source/missing reasons.")
    
    def record_provenance(
        self,
        field_name: str,
        status: FieldStatus,
        source: Optional[str] = None,
        missing_reason: Optional[MissingReason] = None,
    ) -> None:
        """Record provenance for a field."""
        self.provenance[field_name] = FieldProvenance(
            field_name=field_name,
            status=status,
            source=source,
            missing_reason=missing_reason,
        )

    def to_provenance_dict(self) -> dict[str, str | None]:
        """Flatten provenance into a single dict for export or logging."""
        out = {}
        for prov in self.provenance.values():
            out.update(prov.to_dict())
        return out
