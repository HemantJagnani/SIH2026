"""
Canonical Models & Schemas for Cross-Source Fare Reconciliation.
Implements §1, §2, §6, §7, §8, §11, and §12 of the APIx Cross-Source Specification.
"""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field, UUID4, model_validator


class PriceSemantics(str, enum.Enum):
    """
    Explicit semantics for the price rendered by the source per §11.
    Only DISPLAYED_TOTAL qualifies directly for mandatory payable headline index.
    """
    DISPLAYED_TOTAL = "DISPLAYED_TOTAL"
    DISPLAYED_FROM = "DISPLAYED_FROM"
    DISPLAYED_FARE = "DISPLAYED_FARE"
    UNKNOWN_PRICE_DEFINITION = "UNKNOWN_PRICE_DEFINITION"


class MatchStatus(str, enum.Enum):
    """
    Cross-source reconciliation matching status per §5, §7, and §12.
    """
    EXACT_MATCH = "EXACT_MATCH"
    PROBABLE_MATCH = "PROBABLE_MATCH"
    NO_MATCH = "NO_MATCH"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    PRICE_CONFLICT_REVIEW = "PRICE_CONFLICT_REVIEW"
    PRICE_CONSISTENT = "PRICE_CONSISTENT"
    PRICE_VARIANCE_AGGREGATED = "PRICE_VARIANCE_AGGREGATED"
    PRICE_CONFLICT_UNRESOLVED = "PRICE_CONFLICT_UNRESOLVED"


class RawSourceObservation(BaseModel):
    """
    Immutable raw evidence record preserved verbatim from the scraper per §2.
    Never deleted or overwritten. Linked to canonical offers via canonical_offer_id.
    """
    raw_id: str = Field(default_factory=lambda: f"raw_{uuid.uuid4().hex[:12]}")
    source: str
    source_observation_id: Optional[str] = None
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    raw_payload: Dict[str, Any] = Field(default_factory=dict)
    raw_price_text: Optional[str] = None
    canonical_offer_id: Optional[str] = None


class CanonicalOffer(BaseModel):
    """
    Common canonical representation of a flight offer per §1, §6, and §12.
    Contains unified fields, field-level provenance, price by source, and lineage.
    Never fabricates missing data (stores UNKNOWN / NOT_PROVIDED).
    """
    canonical_offer_id: str = Field(default_factory=lambda: f"can_{uuid.uuid4().hex[:12]}")
    
    # ── Core Geographic & Journey Fields ──
    route: str
    origin: str
    destination: str
    travel_date: str
    search_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    lead_time: str
    
    # ── Flight & Operational Fields ──
    airline: str
    airline_code: str = "UNKNOWN"
    flight_number: str
    departure_time: str = "UNKNOWN"
    arrival_time: str = "UNKNOWN"
    duration_minutes: Optional[int] = None
    stops: int = 0
    
    # ── Product Strata & Conditions ──
    cabin: str = "ECONOMY"
    fare_family: str = "NOT_PROVIDED"
    baggage: str = "NOT_PROVIDED"
    cabin_baggage_kg: Optional[int] = None
    checkin_baggage_kg: Optional[int] = None
    refundability: str = "UNKNOWN"
    changeability: str = "UNKNOWN"
    passenger_type: str = "ADULT"
    
    # ── Price Semantics & Monetary Values ──
    total_fare: Optional[Decimal] = None
    currency: str = "INR"
    price_semantics: PriceSemantics = PriceSemantics.DISPLAYED_TOTAL
    
    # ── Source Lineage & Reconciliation (§12) ──
    source: str
    source_observation_ids: List[str] = Field(default_factory=list)
    source_names: List[str] = Field(default_factory=list)
    source_ids: List[str] = Field(default_factory=list)
    source_count: int = 1
    match_status: MatchStatus = MatchStatus.NO_MATCH
    match_confidence: float = 1.0
    field_provenance: Dict[str, str] = Field(default_factory=dict)
    price_by_source: Dict[str, Decimal] = Field(default_factory=dict)
    source_prices: Dict[str, Decimal] = Field(default_factory=dict)
    source_timestamps: Dict[str, str] = Field(default_factory=dict)
    aggregation_method: str = "SINGLE_SOURCE"
    aggregation_source_count: int = 1
    price_conflict: bool = False
    reconciliation_timestamp: Optional[datetime] = None

    # ── Fingerprints (§9) ──
    itinerary_fingerprint: str = ""
    offer_fingerprint: str = ""
    canonical_offer_fingerprint: str = ""

    @model_validator(mode="after")
    def populate_defaults_and_provenance(self) -> CanonicalOffer:
        # Standardize source_names and source_ids
        if not self.source_names and self.source:
            self.source_names = [s.strip() for s in self.source.split(",") if s.strip()]
        if not self.source_ids:
            self.source_ids = list(self.source_names)
        self.source_count = len(self.source_names)
        
        # Populate initial price_by_source and source_prices if empty
        if not self.price_by_source and self.source and self.total_fare is not None:
            self.price_by_source = {self.source: self.total_fare}
        if not self.source_prices and self.price_by_source:
            self.source_prices = dict(self.price_by_source)

        # Populate source_timestamps if empty
        if not self.source_timestamps and self.source:
            ts_str = self.search_timestamp.isoformat() if hasattr(self.search_timestamp, "isoformat") else str(self.search_timestamp)
            self.source_timestamps = {s: ts_str for s in self.source_names}

        # Set default aggregation method and source count
        if self.source_count == 1 and self.aggregation_method == "SINGLE_SOURCE":
            self.aggregation_source_count = 1
            
        # Ensure field_provenance has entries for populated fields
        for field_name in [
            "airline", "flight_number", "departure_time", "arrival_time",
            "stops", "cabin", "fare_family", "baggage", "refundability", "total_fare"
        ]:
            val = getattr(self, field_name, None)
            if val not in (None, "UNKNOWN", "NOT_PROVIDED") and field_name not in self.field_provenance:
                self.field_provenance[field_name] = self.source
        return self


class APIxProductObservation(BaseModel):
    """
    Finalized canonical product observation post-reconciliation, deduplication,
    and product comparability assessment per §8, §12, and §14.
    """
    apix_observation_id: str = Field(default_factory=lambda: f"apix_{uuid.uuid4().hex[:12]}")
    canonical_offer_id: str
    route: str
    origin: str
    destination: str
    travel_date: str
    lead_time: str
    airline: str
    flight_number: str
    departure_time: str
    arrival_time: str
    stops: int
    cabin: str
    fare_family: str
    baggage: str
    refundability: str
    total_fare: Decimal
    currency: str = "INR"
    is_comparable_baseline: bool = True
    non_comparable_reason: Optional[str] = None
    sources_contributing: List[str]
    source_ids: List[str] = Field(default_factory=list)
    source_observation_ids: List[str] = Field(default_factory=list)
    source_count: int = 1
    price_by_source: Dict[str, Decimal]
    source_prices: Dict[str, Decimal] = Field(default_factory=dict)
    source_timestamps: Dict[str, str] = Field(default_factory=dict)
    aggregation_method: str = "SINGLE_SOURCE"
    aggregation_source_count: int = 1
    field_provenance: Dict[str, str] = Field(default_factory=dict)
    match_status: MatchStatus
