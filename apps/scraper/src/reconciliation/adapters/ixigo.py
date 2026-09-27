"""
Reconciliation adapter for Ixigo.
Normalizes Ixigo native raw dictionaries into CanonicalOffer.
"""

from __future__ import annotations

from typing import Any, Dict
from ..models import PriceSemantics, RawSourceObservation
from .base import BaseReconciliationAdapter


class IxigoReconciliationAdapter(BaseReconciliationAdapter):
    @property
    def source_id(self) -> str:
        return "ixigo"

    @property
    def source_name(self) -> str:
        return "Ixigo"

    @property
    def default_price_semantics(self) -> PriceSemantics:
        return PriceSemantics.DISPLAYED_TOTAL

    def normalize(self, raw_record: Dict[str, Any] | RawSourceObservation) -> Any:
        data = raw_record.raw_payload if isinstance(raw_record, RawSourceObservation) else raw_record
        raw_id = (
            raw_record.source_observation_id or raw_record.raw_id
            if isinstance(raw_record, RawSourceObservation)
            else str(data.get("observation_id") or data.get("source_offer_id") or "ixigo_unknown")
        )

        origin = data.get("origin")
        dest = data.get("destination")
        if not origin and "route" in data and "-" in str(data["route"]):
            origin, dest = str(data["route"]).split("-")[:2]

        lead_days = data.get("lead_days", 7)
        lead_time = f"T+{lead_days}" if not str(lead_days).startswith("T+") else str(lead_days)

        return self._build_canonical_offer(
            raw_id=raw_id,
            origin=origin or "DEL",
            destination=dest or "BOM",
            travel_date=str(data.get("travel_date", "")),
            airline=str(data.get("airline", "UNKNOWN")),
            flight_number=str(data.get("flight_number", "UNKNOWN")),
            departure_time=str(data.get("departure_time_local") or data.get("departure_time") or "UNKNOWN"),
            arrival_time=str(data.get("arrival_time_local") or data.get("arrival_time") or "UNKNOWN"),
            total_fare=data.get("total_fare"),
            stops=int(data.get("stops", 0)),
            lead_time=lead_time,
            cabin=str(data.get("cabin", "ECONOMY")).replace("CabinClass.", ""),
            fare_family=str(data.get("fare_family", "STANDARD")),
            baggage=str(data.get("baggage", "NOT_PROVIDED")),
            cabin_baggage_kg=data.get("cabin_baggage_kg"),
            checkin_baggage_kg=data.get("checkin_baggage_kg"),
            refundability=str(data.get("refundability", "UNKNOWN")),
            changeability=str(data.get("changeability", "UNKNOWN")),
            passenger_type="ADULT",
            currency=str(data.get("currency", "INR")),
            price_semantics=self.default_price_semantics,
        )
