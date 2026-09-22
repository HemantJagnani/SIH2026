"""
FareObservation — the canonical record for a single flight fare offer.

This is the central data contract for the entire pipeline. Every source
adapter, normalizer, and validator works toward producing a valid
FareObservation. Every field defined in spec §13 is represented here.

IMPORTANT (spec §47): The schema of FareObservation must NOT be changed
without explicit approval. A schema version bump is required for any change.

Source: spec §13, §15, §25, §26, §44 Phase 1.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field, UUID4, field_validator, model_validator

from .enums import AvailabilityStatus, CabinClass, TripType
from .version import SCHEMA_VERSION


class FareObservation(BaseModel):
    """
    Canonical record for a single flight fare offer collected by the pipeline.

    Minimum schema from spec §13. Additional source-specific fields may be
    added as subclasses or optional extras — but the fields defined here
    form the immutable contract.

    Key design principles (spec §15):
    - Raw values are preserved alongside normalized values.
    - Normalization outputs are separate fields, never overwrites.
    - schema_version is stamped on every record.
    """

    # -----------------------------------------------------------------------
    # Identity
    # -----------------------------------------------------------------------

    observation_id: UUID4 = Field(
        default_factory=uuid.uuid4,
        description="Unique identifier for this canonical fare observation.",
    )

    # -----------------------------------------------------------------------
    # Collection provenance
    # -----------------------------------------------------------------------

    collection_run_id: UUID4 = Field(
        ...,
        description="Parent collection run that produced this observation.",
    )
    source: str = Field(
        ...,
        description="Source identifier (e.g. 'indigo', 'cleartrip').",
    )
    source_offer_id: str | None = Field(
        default=None,
        description="The source's own offer/itinerary identifier, if provided.",
    )
    source_itinerary_id: str | None = Field(
        default=None,
        description="Ignav itinerary ID or equivalent, as source metadata.",
    )
    # The URL of the page/endpoint where the fare was sourced. Stored for
    # auditability and to detect URL changes (schema_change detection).
    source_url: str | None = Field(
        default=None,
        description="URL of the source page or API endpoint at collection time.",
    )

    # -----------------------------------------------------------------------
    # Collection timing
    # -----------------------------------------------------------------------

    collected_at: datetime = Field(
        ...,
        description="UTC datetime when this fare was collected from the source.",
    )
    # search_timestamp records when the search was initiated, which can
    # differ from collected_at if extraction takes time (e.g. slow JS render).
    search_timestamp: datetime | None = Field(
        default=None,
        description="UTC datetime when the search was initiated (may differ from collected_at).",
    )

    # -----------------------------------------------------------------------
    # Travel details
    # -----------------------------------------------------------------------

    travel_date: date = Field(
        ...,
        description="Date of the flight (YYYY-MM-DD).",
    )
    lead_days: int = Field(
        ...,
        ge=0,
        description="Days between collection date and travel_date. lead_days = travel_date - collection_date.",
    )

    # -----------------------------------------------------------------------
    # Route
    # -----------------------------------------------------------------------

    origin: str = Field(
        ...,
        min_length=3,
        max_length=3,
        description="Departure airport IATA code.",
    )
    destination: str = Field(
        ...,
        min_length=3,
        max_length=3,
        description="Arrival airport IATA code.",
    )

    # -----------------------------------------------------------------------
    # Airline
    # -----------------------------------------------------------------------

    airline: str = Field(
        ...,
        description="Canonical airline name (e.g. 'IndiGo').",
    )
    airline_code: str | None = Field(
        default=None,
        description="IATA/ICAO airline designator (e.g. '6E' for IndiGo).",
    )
    flight_number: str | None = Field(
        default=None,
        description="Flight number as provided by the source (e.g. '6E-123').",
    )

    # -----------------------------------------------------------------------
    # Itinerary
    # -----------------------------------------------------------------------

    trip_type: TripType = Field(
        ...,
        description="ONE_WAY or ROUND_TRIP.",
    )
    cabin: CabinClass = Field(
        ...,
        description="Cabin class of this fare offer.",
    )
    passenger_count: int = Field(
        ...,
        ge=1,
        description="Total number of passengers this fare covers.",
    )

    # -----------------------------------------------------------------------
    # Scheduling
    # -----------------------------------------------------------------------

    departure_time_local: datetime | None = Field(
        default=None,
        description="Scheduled departure datetime (local airport time).",
    )
    departure_time_utc: datetime | None = Field(
        default=None,
        description="Scheduled departure datetime (UTC).",
    )
    arrival_time_local: datetime | None = Field(
        default=None,
        description="Scheduled arrival datetime (local airport time).",
    )
    arrival_time_utc: datetime | None = Field(
        default=None,
        description="Scheduled arrival datetime (UTC).",
    )
    stops: int | None = Field(
        default=None,
        ge=0,
        description="Number of stops (0 = non-stop).",
    )

    # -----------------------------------------------------------------------
    # Fare classification
    # -----------------------------------------------------------------------

    fare_family: str | None = Field(
        default=None,
        description="Fare family name as given by the source (e.g. 'SAVER', 'FLEX').",
    )
    fare_class: str | None = Field(
        default=None,
        description="Booking class / RBD code (e.g. 'Q', 'Y').",
    )
    requires_self_transfer: bool | None = Field(
        default=None,
        description="True if the itinerary requires a self-transfer.",
    )

    # -----------------------------------------------------------------------
    # Pricing — spec §25 / §26
    # All decimal values are in the currency specified by the `currency` field.
    # Methodology note: total_fare is the project's target price concept for the
    # POC (total consumer-facing payable amount, excl. optional ancillaries).
    # Never mix base_fare from one source with total_fare from another.
    # -----------------------------------------------------------------------

    base_fare: Annotated[Decimal | None, Field(
        default=None,
        ge=0,
        description="Base fare component before taxes and fees.",
    )] = None
    taxes: Annotated[Decimal | None, Field(
        default=None,
        ge=0,
        description="Total taxes component.",
    )] = None
    fees: Annotated[Decimal | None, Field(
        default=None,
        ge=0,
        description="Total fees/surcharges component.",
    )] = None
    # airport_charges and convenience_fee are separated per Phase 9 spec
    # to support sources (like OTAs) that expose these as distinct line items.
    # Do not manufacture these from a total fare - leave null if not provided.
    airport_charges: Annotated[Decimal | None, Field(
        default=None,
        ge=0,
        description="Airport statutory charges, if exposed separately by source.",
    )] = None
    convenience_fee: Annotated[Decimal | None, Field(
        default=None,
        ge=0,
        description="OTA or booking convenience fee, if exposed separately by source.",
    )] = None
    discount: Annotated[Decimal | None, Field(
        default=None,
        ge=0,
        description="Any discount applied to the fare.",
    )] = None
    total_fare: Annotated[Decimal | None, Field(
        default=None,
        ge=0,
        description=(
            "Total consumer-payable amount. "
            "Project target price concept for POC (spec §25, docs/decisions/fare-concept.md)."
        ),
    )] = None
    currency: str = Field(
        default="INR",
        description="ISO 4217 currency code. Must be INR for this project.",
    )
    price_status: str | None = Field(
        default=None,
        description="Status of the price, e.g. verified or unverified.",
    )

    # -----------------------------------------------------------------------
    # Availability — spec §20
    # IMPORTANT: SOLD_OUT != price=0. Never interpret sold-out as zero price.
    # -----------------------------------------------------------------------

    availability: AvailabilityStatus = Field(
        ...,
        description="Availability of this fare offer. SOLD_OUT is never zero price.",
    )

    # -----------------------------------------------------------------------
    # Raw value preservation — spec §15
    # Raw source values are preserved alongside normalized canonical values
    # so the normalizer output can always be audited against the source.
    # -----------------------------------------------------------------------

    raw_value_reference: str | None = Field(
        default=None,
        description=(
            "Reference key pointing to the raw field values used to produce "
            "this observation (e.g. a dict serialized as JSON, or a key into "
            "the raw_evidence_uri document)."
        ),
    )
    raw_evidence_uri: str | None = Field(
        default=None,
        description=(
            "URI pointing to the raw source payload in object storage. "
            "Matches the raw_evidence_uri on the corresponding RawObservation."
        ),
    )

    # -----------------------------------------------------------------------
    # Versioning — spec §44 Phase 1
    # All three version fields are required so downstream systems can detect
    # schema/adapter/normalizer changes without inspecting data content.
    # -----------------------------------------------------------------------

    adapter_version: str = Field(
        ...,
        description="Semver of the adapter that collected and mapped this observation.",
    )
    normalizer_version: str = Field(
        ...,
        description="Semver of the normalizer that standardized this observation.",
    )
    schema_version: str = Field(
        default=SCHEMA_VERSION,
        description="Version of the FareObservation schema. Must match SCHEMA_VERSION constant.",
    )

    # -----------------------------------------------------------------------
    # Validators
    # -----------------------------------------------------------------------

    @field_validator("origin", "destination", mode="before")
    @classmethod
    def uppercase_iata(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("currency", mode="before")
    @classmethod
    def uppercase_currency(cls, v: str) -> str:
        return v.strip().upper()

    @model_validator(mode="after")
    def origin_not_equal_to_destination(self) -> "FareObservation":
        """Route must have distinct origin and destination. Spec §20."""
        if self.origin == self.destination:
            raise ValueError(
                f"origin and destination must differ; got '{self.origin}' for both."
            )
        return self

    @model_validator(mode="after")
    def travel_date_not_before_collected_at(self) -> "FareObservation":
        """Travel date must not be in the past relative to collection. Spec §20."""
        collection_date = self.collected_at.date()
        if self.travel_date < collection_date:
            raise ValueError(
                f"travel_date ({self.travel_date}) must be >= collection date ({collection_date})."
            )
        return self

    @model_validator(mode="after")
    def schema_version_must_match_constant(self) -> "FareObservation":
        """Catch accidental schema version mismatches early."""
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(
                f"schema_version mismatch: record has '{self.schema_version}', "
                f"current constant is '{SCHEMA_VERSION}'."
            )
        return self
