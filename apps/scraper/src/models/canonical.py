"""
Canonical Data Models for APIx Phase 2.
Implements RawFareObservation, NormalizedFareObservation, and ProductStratum
per Methodology §4.2, §5, §6, §7.1, §7.2, and §10A.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional
from pydantic import BaseModel, Field, UUID4, field_validator, model_validator

from .enums import AvailabilityStatus, CabinClass, TripType
from .fingerprint import compute_itinerary_fingerprint, compute_offer_fingerprint


# ---------------------------------------------------------------------------
# Helper Classification Functions (§5)
# ---------------------------------------------------------------------------

def classify_travel_day_type(travel_date: date) -> str:
    """Classifies flight date into WEEKDAY (Mon-Thu) or WEEKEND (Fri-Sun)."""
    # weekday() is 0 for Monday, 6 for Sunday
    if travel_date.weekday() in (0, 1, 2, 3):
        return "WEEKDAY"
    return "WEEKEND"


def classify_departure_time_band(departure_time: Optional[datetime | str]) -> str:
    """
    Classifies flight departure time into 4 standard daily bands:
    - EARLY_MORNING: 00:00 - 05:59
    - MORNING:       06:00 - 11:59
    - AFTERNOON:     12:00 - 17:59
    - EVENING:       18:00 - 23:59
    """
    if departure_time is None:
        return "UNKNOWN_BAND"
    
    hour = None
    if isinstance(departure_time, datetime):
        hour = departure_time.hour
    elif isinstance(departure_time, str):
        s = departure_time.strip()
        if "T" in s:
            s = s.split("T")[-1]
        parts = s.split(":")
        if parts and parts[0].isdigit():
            hour = int(parts[0])
            
    if hour is None:
        return "UNKNOWN_BAND"
        
    if 0 <= hour < 6:
        return "EARLY_MORNING"
    elif 6 <= hour < 12:
        return "MORNING"
    elif 12 <= hour < 18:
        return "AFTERNOON"
    else:
        return "EVENING"


def classify_lead_time_class(lead_days: int) -> str:
    """Maps lead days into standard strata: T+1, T+7, T+15, T+21, T+30, T+45, etc."""
    standard_windows = {1, 7, 15, 21, 30, 45, 60}
    if lead_days in standard_windows:
        return f"T+{lead_days}"
    return f"T+{lead_days}" if lead_days >= 0 else "PAST"


def classify_stop_category(stops: Optional[int]) -> str:
    """Classifies number of stops into NONSTOP, ONE_STOP, or MULTI_STOP."""
    if stops is None or stops == 0:
        return "NONSTOP"
    elif stops == 1:
        return "ONE_STOP"
    return "MULTI_STOP"


# ---------------------------------------------------------------------------
# Product Stratum (§5)
# ---------------------------------------------------------------------------

class ProductStratum(BaseModel):
    """
    Defines a homogeneous, comparable airfare product stratum per Methodology §5.
    
    product_stratum_id = hash(
        origin, destination, travel_day_type, departure_time_band,
        cabin, fare_family_group, baggage_group, stop_category,
        passenger_type, lead_time_class
    )
    """
    origin: str
    destination: str
    travel_day_type: str = "WEEKDAY"
    departure_time_band: str = "MORNING"
    cabin: str = "ECONOMY"
    fare_family_group: str = "STANDARD"
    baggage_group: str = "STANDARD"
    stop_category: str = "NONSTOP"
    passenger_type: str = "ADULT"
    lead_time_class: str = "T+7"

    @property
    def stratum_id(self) -> str:
        canonical_str = (
            f"{self.origin.upper()}|{self.destination.upper()}|"
            f"{self.travel_day_type.upper()}|{self.departure_time_band.upper()}|"
            f"{self.cabin.upper()}|{self.fare_family_group.upper()}|"
            f"{self.baggage_group.upper()}|{self.stop_category.upper()}|"
            f"{self.passenger_type.upper()}|{self.lead_time_class.upper()}"
        )
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    @classmethod
    def from_observation(cls, obs: Any) -> ProductStratum:
        """Constructs ProductStratum directly from an observation."""
        origin = getattr(obs, "origin", "DEL")
        destination = getattr(obs, "destination", "BOM")
        
        # Day type
        travel_date = getattr(obs, "travel_date", None)
        day_type = classify_travel_day_type(travel_date) if travel_date else "WEEKDAY"
        
        # Departure band
        dep_time = getattr(obs, "departure_time_local", None)
        dep_band = classify_departure_time_band(dep_time)
        
        # Cabin
        cabin = getattr(obs, "cabin", "ECONOMY") or "ECONOMY"
        if isinstance(cabin, CabinClass):
            cabin = cabin.value
            
        # Fare family
        fare_fam = getattr(obs, "fare_family", None) or "STANDARD"
        
        # Baggage group
        baggage = getattr(obs, "baggage_allowance", None) or "STANDARD"
        
        # Stops
        stops = getattr(obs, "stops", 0)
        stop_cat = classify_stop_category(stops)
        
        # Lead time
        lead_days = getattr(obs, "lead_days", 7)
        lead_class = classify_lead_time_class(lead_days)
        
        return cls(
            origin=origin,
            destination=destination,
            travel_day_type=day_type,
            departure_time_band=dep_band,
            cabin=str(cabin).upper(),
            fare_family_group=str(fare_fam).upper(),
            baggage_group=str(baggage).upper(),
            stop_category=stop_cat,
            passenger_type="ADULT",
            lead_time_class=lead_class,
        )


# ---------------------------------------------------------------------------
# RawFareObservation (§7.1)
# ---------------------------------------------------------------------------

class RawFareObservation(BaseModel):
    """
    Immutable raw evidence record for a single scraped flight offer.
    Stores verbatim strings, source timestamps, and raw payloads for auditability.
    """
    observation_id: UUID4 = Field(default_factory=uuid.uuid4)
    collection_run_id: UUID4 = Field(default_factory=uuid.uuid4)
    
    source: str = Field(..., description="e.g. 'easemytrip', 'ignav', 'indigo'")
    source_type: str = Field(default="OTA", description="OTA, AIRLINE, AGGREGATOR")
    source_url: Optional[str] = None
    
    search_timestamp_utc: datetime = Field(default_factory=datetime.utcnow)
    search_timestamp_local: Optional[datetime] = None
    
    origin_raw: str
    destination_raw: str
    travel_date_raw: str
    lead_days_raw: int
    
    airline_raw: Optional[str] = None
    flight_number_raw: Optional[str] = None
    departure_time_raw: Optional[str] = None
    arrival_time_raw: Optional[str] = None
    duration_raw: Optional[str] = None
    stops_raw: Optional[str] = None
    
    price_raw: Optional[str] = None
    currency_raw: Optional[str] = "INR"
    
    raw_payload: dict[str, Any] = Field(default_factory=dict)
    raw_evidence_uri: Optional[str] = None
    
    parser_version: str = "1.0.0"
    schema_version: str = "1.1.0"
    collection_agent_version: str = "1.0.0"


# ---------------------------------------------------------------------------
# NormalizedFareObservation (§7.2)
# ---------------------------------------------------------------------------

class NormalizedFareObservation(BaseModel):
    """
    Canonical, validated, and normalized fare observation ready for index compilation.
    Enforces Decimal monetary precision, valid INR, fingerprints, and quality status.
    """
    observation_id: UUID4 = Field(default_factory=uuid.uuid4)
    raw_observation_id: UUID4 = Field(default_factory=uuid.uuid4)
    collection_run_id: UUID4
    
    # Provenance
    source: str
    source_type: str = "OTA"
    source_offer_id: Optional[str] = None
    source_itinerary_id: Optional[str] = None
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    search_timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Route & Schedule
    origin: str = Field(..., min_length=3, max_length=3)
    destination: str = Field(..., min_length=3, max_length=3)
    route: str = Field(default="")
    travel_date: date
    travel_day_of_week: int = Field(default=1, ge=1, le=7)
    travel_day_type: str = "WEEKDAY"
    lead_days: int = Field(ge=0)
    lead_time_class: str = "T+7"
    
    # Flight details
    airline: str
    airline_code: str = ""
    flight_number: str
    departure_time_local: Optional[datetime] = None
    arrival_time_local: Optional[datetime] = None
    departure_time_band: str = "MORNING"
    duration_minutes: Optional[int] = None
    stops: int = 0
    stop_category: str = "NONSTOP"
    
    # Product quality dimensions
    cabin: str = "ECONOMY"
    fare_family: Optional[str] = "STANDARD"
    fare_family_group: str = "STANDARD"
    baggage_allowance: Optional[str] = "STANDARD"
    baggage_group: str = "STANDARD"
    refundability: Optional[str] = "UNKNOWN"
    changeability: Optional[str] = "UNKNOWN"
    passenger_type: str = "ADULT"
    
    # Monetary values (MUST be Decimal, never Float)
    base_fare: Optional[Decimal] = None
    taxes: Optional[Decimal] = None
    airport_charges: Optional[Decimal] = None
    mandatory_fees: Optional[Decimal] = None
    total_fare: Decimal = Field(..., gt=Decimal("0"))
    normalized_price_inr: Decimal = Field(..., gt=Decimal("0"))
    currency: str = "INR"
    
    # Operational & Quality status
    availability: str = "AVAILABLE"
    quality_status: str = "VALID"
    duplicate_group_id: Optional[str] = None
    
    # Statistical Fingerprints
    itinerary_fingerprint: str = ""
    offer_fingerprint: str = ""
    product_stratum_id: str = ""
    product_key: str = ""
    
    # Temporal grouping helpers
    month: str = ""
    week: str = ""
    day: str = ""
    
    schema_version: str = "1.1.0"
    methodology_version: str = "APIx v1.0"

    @field_validator("currency")
    @classmethod
    def validate_inr(cls, v: str) -> str:
        if v.upper() != "INR":
            raise ValueError(f"APIx only accepts INR currency, got {v}")
        return "INR"

    @model_validator(mode="before")
    @classmethod
    def compute_derived_fields(cls, values: dict[str, Any]) -> dict[str, Any]:
        # Origin/destination normalization
        origin = str(values.get("origin", "")).strip().upper()
        destination = str(values.get("destination", "")).strip().upper()
        values["origin"] = origin
        values["destination"] = destination
        values["route"] = f"{origin}-{destination}"
        
        # Travel date derived fields
        t_date = values.get("travel_date")
        if isinstance(t_date, str):
            t_date = date.fromisoformat(t_date)
            values["travel_date"] = t_date
            
        if isinstance(t_date, date):
            values["travel_day_of_week"] = t_date.isoweekday()
            values["travel_day_type"] = classify_travel_day_type(t_date)
            values["month"] = t_date.strftime("%Y-%m")
            values["week"] = t_date.strftime("%Y-W%W")
            values["day"] = t_date.strftime("%Y-%m-%d")
            
        # Lead time class
        lead_days = values.get("lead_days", 7)
        values["lead_time_class"] = classify_lead_time_class(lead_days)
        
        # Departure band
        dep_time = values.get("departure_time_local")
        values["departure_time_band"] = classify_departure_time_band(dep_time)
        
        # Stop category
        stops = values.get("stops", 0)
        values["stop_category"] = classify_stop_category(stops)
        
        # Monetary precision
        total_fare = values.get("total_fare")
        if total_fare is not None and not isinstance(total_fare, Decimal):
            total_fare = Decimal(str(total_fare))
            values["total_fare"] = total_fare
            
        if "normalized_price_inr" not in values or values["normalized_price_inr"] is None:
            values["normalized_price_inr"] = total_fare
        elif not isinstance(values["normalized_price_inr"], Decimal):
            values["normalized_price_inr"] = Decimal(str(values["normalized_price_inr"]))

        # Derive airline code from flight number if missing
        flight_num = str(values.get("flight_number", "")).strip().upper()
        if not values.get("airline_code"):
            if "-" in flight_num:
                values["airline_code"] = flight_num.split("-")[0]
            elif len(flight_num) >= 2 and flight_num[:2].isalpha():
                values["airline_code"] = flight_num[:2]

        # Deterministic Fingerprints
        itin_fp = values.get("itinerary_fingerprint")
        if not itin_fp:
            itin_fp = compute_itinerary_fingerprint(
                origin=origin,
                destination=destination,
                travel_date=t_date,
                airline=values.get("airline", ""),
                flight_number=flight_num,
                departure_time=dep_time,
                arrival_time=values.get("arrival_time_local"),
                stops=stops,
            )
            values["itinerary_fingerprint"] = itin_fp

        offer_fp = values.get("offer_fingerprint")
        if not offer_fp:
            offer_fp = compute_offer_fingerprint(
                itinerary_fingerprint=itin_fp,
                fare_family=values.get("fare_family", "STANDARD"),
                cabin=values.get("cabin", "ECONOMY"),
                baggage=values.get("baggage_allowance", "STANDARD"),
                refundability=values.get("refundability", "UNKNOWN"),
                changeability=values.get("changeability", "UNKNOWN"),
            )
            values["offer_fingerprint"] = offer_fp

        # Product Stratum
        stratum_id = values.get("product_stratum_id")
        if not stratum_id:
            stratum = ProductStratum(
                origin=origin,
                destination=destination,
                travel_day_type=values["travel_day_type"],
                departure_time_band=values["departure_time_band"],
                cabin=str(values.get("cabin", "ECONOMY")).upper(),
                fare_family_group=str(values.get("fare_family_group", "STANDARD")).upper(),
                baggage_group=str(values.get("baggage_group", "STANDARD")).upper(),
                stop_category=values["stop_category"],
                passenger_type="ADULT",
                lead_time_class=values["lead_time_class"],
            )
            values["product_stratum_id"] = stratum.stratum_id

        # Product Key (for cross-period matching of the same flight offering within stratum)
        prod_key = values.get("product_key")
        if not prod_key:
            norm_airline = str(values.get("airline", "")).strip().upper()
            norm_flight = flight_num
            stratum_ref = values["product_stratum_id"]
            prod_canonical = f"{stratum_ref}|{norm_airline}|{norm_flight}"
            values["product_key"] = hashlib.sha256(prod_canonical.encode("utf-8")).hexdigest()

        return values
