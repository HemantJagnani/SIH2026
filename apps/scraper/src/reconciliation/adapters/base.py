"""
Base class for source normalization adapters.
Implements §3 and §6 of the APIx Cross-Source Specification.
"""

from __future__ import annotations

import abc
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional

from ..fingerprint import (
    compute_canonical_offer_fingerprint,
    compute_itinerary_fingerprint,
    compute_offer_fingerprint,
    normalize_flight_number,
    normalize_time_str,
)
from ..models import CanonicalOffer, PriceSemantics, RawSourceObservation


class BaseReconciliationAdapter(abc.ABC):
    """
    Abstract adapter for converting source-specific raw observations
    into standardized CanonicalOffer objects.
    
    Responsibilities:
    1. Extract source fields without mutating raw records.
    2. Convert types (e.g. monetary string -> Decimal).
    3. Retain field-level provenance for every extracted attribute.
    4. Store UNKNOWN / NOT_PROVIDED for missing fields without fabrication.
    5. Compute deterministic fingerprints.
    """

    @property
    @abc.abstractmethod
    def source_id(self) -> str:
        """Identifier for the source (e.g. 'google_flights', 'easemytrip', 'ixigo')."""
        pass

    @property
    @abc.abstractmethod
    def source_name(self) -> str:
        """Display name for the source."""
        pass

    @property
    def default_price_semantics(self) -> PriceSemantics:
        """Default price semantics exposed by this source."""
        return PriceSemantics.DISPLAYED_TOTAL

    @abc.abstractmethod
    def normalize(self, raw_record: Dict[str, Any] | RawSourceObservation) -> CanonicalOffer:
        """Normalize native source dictionary or RawSourceObservation into CanonicalOffer."""
        pass

    def _build_canonical_offer(
        self,
        raw_id: str,
        origin: str,
        destination: str,
        travel_date: str,
        airline: str,
        flight_number: str,
        departure_time: str,
        arrival_time: str,
        total_fare: Optional[Decimal | float | str],
        stops: int = 0,
        lead_time: str = "T+7",
        duration_minutes: Optional[int] = None,
        cabin: str = "ECONOMY",
        fare_family: str = "NOT_PROVIDED",
        baggage: str = "NOT_PROVIDED",
        cabin_baggage_kg: Optional[int] = None,
        checkin_baggage_kg: Optional[int] = None,
        refundability: str = "UNKNOWN",
        changeability: str = "UNKNOWN",
        passenger_type: str = "ADULT",
        currency: str = "INR",
        price_semantics: Optional[PriceSemantics] = None,
        search_timestamp: Optional[datetime] = None,
    ) -> CanonicalOffer:
        """Convenience builder ensuring strict provenance and fingerprint computation."""
        norm_origin = str(origin).strip().upper()
        norm_dest = str(destination).strip().upper()
        route = f"{norm_origin}-{norm_dest}"
        norm_fn = normalize_flight_number(flight_number)
        norm_dep = normalize_time_str(departure_time)
        norm_arr = normalize_time_str(arrival_time)
        
        # Total fare conversion to Decimal
        fare_dec: Optional[Decimal] = None
        if total_fare is not None and str(total_fare).strip():
            try:
                # Clean any currency symbols or commas
                cleaned_price = str(total_fare).replace("₹", "").replace(",", "").strip()
                fare_dec = Decimal(cleaned_price)
            except Exception:
                fare_dec = None

        semantics = price_semantics or self.default_price_semantics

        # Build field provenance map
        provenance = {
            "origin": self.source_id,
            "destination": self.source_id,
            "route": self.source_id,
            "travel_date": self.source_id,
            "airline": self.source_id,
            "flight_number": self.source_id,
            "departure_time": self.source_id,
            "stops": self.source_id,
            "cabin": self.source_id,
        }
        if arrival_time not in ("UNKNOWN", "NOT_PROVIDED"):
            provenance["arrival_time"] = self.source_id
        if fare_family not in ("UNKNOWN", "NOT_PROVIDED"):
            provenance["fare_family"] = self.source_id
        if baggage not in ("UNKNOWN", "NOT_PROVIDED"):
            provenance["baggage"] = self.source_id
        if refundability not in ("UNKNOWN", "NOT_PROVIDED"):
            provenance["refundability"] = self.source_id
        if fare_dec is not None:
            provenance["total_fare"] = self.source_id

        # Compute fingerprints
        itin_fp = compute_itinerary_fingerprint(
            origin=norm_origin,
            destination=norm_dest,
            travel_date=travel_date,
            airline=airline,
            flight_number=norm_fn,
            departure_time=norm_dep,
        )
        offer_fp = compute_offer_fingerprint(
            itinerary_fp=itin_fp,
            cabin=cabin,
            fare_family=fare_family,
            baggage=baggage,
            refundability=refundability,
            passenger_type=passenger_type,
        )
        can_fp = compute_canonical_offer_fingerprint(
            route=route,
            travel_date=travel_date,
            airline=airline,
            flight_number=norm_fn,
            departure_time=norm_dep,
            stops=stops,
            cabin=cabin,
            fare_family=fare_family,
            baggage=baggage,
            refundability=refundability,
            passenger_type=passenger_type,
        )

        return CanonicalOffer(
            route=route,
            origin=norm_origin,
            destination=norm_dest,
            travel_date=str(travel_date),
            search_timestamp=search_timestamp or datetime.now(timezone.utc),
            lead_time=lead_time,
            airline=airline,
            flight_number=norm_fn,
            departure_time=norm_dep,
            arrival_time=norm_arr,
            duration_minutes=duration_minutes,
            stops=stops,
            cabin=cabin,
            fare_family=fare_family,
            baggage=baggage,
            cabin_baggage_kg=cabin_baggage_kg,
            checkin_baggage_kg=checkin_baggage_kg,
            refundability=refundability,
            changeability=changeability,
            passenger_type=passenger_type,
            total_fare=fare_dec,
            currency=currency,
            price_semantics=semantics,
            source=self.source_id,
            source_observation_ids=[raw_id],
            source_names=[self.source_id],
            source_count=1,
            field_provenance=provenance,
            price_by_source={self.source_id: fare_dec} if fare_dec else {},
            itinerary_fingerprint=itin_fp,
            offer_fingerprint=offer_fp,
            canonical_offer_fingerprint=can_fp,
        )
