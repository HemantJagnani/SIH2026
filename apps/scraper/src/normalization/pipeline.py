"""
Canonical Normalization Pipeline for APIx Phase 2.
Transforms raw fare observations and scraped records into NormalizedFareObservation.
Implements quality checks, Decimal monetary precision, and deterministic fingerprints.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid

from models.canonical import (
    NormalizedFareObservation,
    ProductStratum,
    classify_travel_day_type,
    classify_departure_time_band,
    classify_lead_time_class,
    classify_stop_category,
)
from models.fingerprint import compute_itinerary_fingerprint, compute_offer_fingerprint

logger = logging.getLogger(__name__)


def normalize_record(raw_dict: Dict[str, Any]) -> Optional[NormalizedFareObservation]:
    """
    Normalizes a single raw fare record into a canonical NormalizedFareObservation.
    
    Validates:
    - Currency must be INR
    - Total fare must be > 0 and convertible to Decimal
    - Origin and destination must be valid 3-letter IATA codes
    - Travel date must be a valid date
    """
    try:
        # 1. Currency validation
        currency = str(raw_dict.get("currency", "INR")).strip().upper()
        if currency != "INR":
            logger.warning(f"Rejected non-INR record: {currency}")
            return None

        # 2. Fare validation & Decimal conversion
        total_fare_raw = raw_dict.get("total_fare")
        if total_fare_raw is None:
            return None
        
        try:
            total_fare = Decimal(str(total_fare_raw).replace(",", "").strip())
            if total_fare <= Decimal("0"):
                return None
        except Exception:
            return None

        # Optional component fares (must be Decimal or None)
        base_fare = None
        if raw_dict.get("base_fare") is not None:
            try:
                base_fare = Decimal(str(raw_dict["base_fare"]).replace(",", "").strip())
            except Exception:
                base_fare = None

        taxes = None
        if raw_dict.get("taxes") is not None:
            try:
                taxes = Decimal(str(raw_dict["taxes"]).replace(",", "").strip())
            except Exception:
                taxes = None

        # 3. Route & Dates
        origin = str(raw_dict.get("origin", "")).strip().upper()
        destination = str(raw_dict.get("destination", "")).strip().upper()
        if len(origin) != 3 or len(destination) != 3:
            return None

        travel_date_val = raw_dict.get("travel_date")
        if isinstance(travel_date_val, str):
            travel_date = date.fromisoformat(travel_date_val.split("T")[0])
        elif isinstance(travel_date_val, date):
            travel_date = travel_date_val
        else:
            return None

        # 4. Lead days & class
        lead_days = raw_dict.get("lead_days", 7)
        if isinstance(lead_days, str):
            lead_days = int(lead_days)
        lead_time_class = classify_lead_time_class(lead_days)

        # 5. Timing extraction
        dep_time = raw_dict.get("departure_time_local")
        arr_time = raw_dict.get("arrival_time_local")
        
        if isinstance(dep_time, str):
            try:
                dep_time = datetime.fromisoformat(dep_time.replace("Z", "+00:00"))
            except Exception:
                dep_time = None
                
        if isinstance(arr_time, str):
            try:
                arr_time = datetime.fromisoformat(arr_time.replace("Z", "+00:00"))
            except Exception:
                arr_time = None

        dep_band = classify_departure_time_band(dep_time)
        day_type = classify_travel_day_type(travel_date)

        # 6. Flight details
        airline = str(raw_dict.get("airline", "UNKNOWN")).strip()
        flight_number = str(raw_dict.get("flight_number", "UNKNOWN")).strip().upper()
        
        airline_code = str(raw_dict.get("airline_code", "")).strip().upper()
        if not airline_code:
            if "-" in flight_number:
                airline_code = flight_number.split("-")[0]
            elif len(flight_number) >= 2 and flight_number[:2].isalpha():
                airline_code = flight_number[:2]

        stops = raw_dict.get("stops")
        if stops is None:
            stops = 0
        elif isinstance(stops, str):
            stops = int(stops)
        stop_cat = classify_stop_category(stops)

        cabin = str(raw_dict.get("cabin", "ECONOMY")).strip().upper()
        fare_family = raw_dict.get("fare_family") or "STANDARD"
        baggage = raw_dict.get("baggage_allowance") or "STANDARD"

        # 7. Fingerprints
        itin_fp = compute_itinerary_fingerprint(
            origin=origin,
            destination=destination,
            travel_date=travel_date,
            airline=airline,
            flight_number=flight_number,
            departure_time=dep_time,
            arrival_time=arr_time,
            stops=stops,
        )

        offer_fp = compute_offer_fingerprint(
            itinerary_fingerprint=itin_fp,
            fare_family=fare_family,
            cabin=cabin,
            baggage=baggage,
            refundability=raw_dict.get("refundability", "UNKNOWN"),
            changeability=raw_dict.get("changeability", "UNKNOWN"),
        )

        # 8. Product Stratum
        stratum = ProductStratum(
            origin=origin,
            destination=destination,
            travel_day_type=day_type,
            departure_time_band=dep_band,
            cabin=cabin,
            fare_family_group=str(fare_family).upper(),
            baggage_group=str(baggage).upper(),
            stop_category=stop_cat,
            passenger_type="ADULT",
            lead_time_class=lead_time_class,
        )

        # 9. Quality status
        avail = str(raw_dict.get("availability", "AVAILABLE")).upper()
        quality_status = "VALID"
        if "SOLD_OUT" in avail:
            quality_status = "SOLD_OUT"
        elif total_fare > Decimal("50000"):
            quality_status = "OUTLIER_REVIEW"

        obs_id = raw_dict.get("observation_id")
        obs_uuid = uuid.UUID(str(obs_id)) if obs_id else uuid.uuid4()
        
        run_id = raw_dict.get("collection_run_id")
        run_uuid = uuid.UUID(str(run_id)) if run_id else uuid.uuid4()

        return NormalizedFareObservation(
            observation_id=obs_uuid,
            raw_observation_id=uuid.uuid4(),
            collection_run_id=run_uuid,
            source=str(raw_dict.get("source", "easemytrip")),
            source_type=str(raw_dict.get("source_type", "OTA")),
            source_offer_id=raw_dict.get("source_offer_id"),
            source_itinerary_id=raw_dict.get("source_itinerary_id"),
            origin=origin,
            destination=destination,
            route=f"{origin}-{destination}",
            travel_date=travel_date,
            travel_day_of_week=travel_date.isoweekday(),
            travel_day_type=day_type,
            lead_days=lead_days,
            lead_time_class=lead_time_class,
            airline=airline,
            airline_code=airline_code,
            flight_number=flight_number,
            departure_time_local=dep_time,
            arrival_time_local=arr_time,
            departure_time_band=dep_band,
            duration_minutes=raw_dict.get("duration_minutes"),
            stops=stops,
            stop_category=stop_cat,
            cabin=cabin,
            fare_family=fare_family,
            fare_family_group=str(fare_family).upper(),
            baggage_allowance=baggage,
            baggage_group=str(baggage).upper(),
            base_fare=base_fare,
            taxes=taxes,
            total_fare=total_fare,
            normalized_price_inr=total_fare,
            currency="INR",
            availability=avail,
            quality_status=quality_status,
            itinerary_fingerprint=itin_fp,
            offer_fingerprint=offer_fp,
            product_stratum_id=stratum.stratum_id,
            month=travel_date.strftime("%Y-%m"),
            week=travel_date.strftime("%Y-W%W"),
            day=travel_date.strftime("%Y-%m-%d"),
        )
    except Exception as e:
        logger.error(f"Error normalizing record: {e}", exc_info=True)
        return None


def normalize_dataset(records: List[Dict[str, Any]]) -> List[NormalizedFareObservation]:
    """Normalizes a list of raw records, tags offer duplicates, and returns valid normalized observations."""
    normalized_list: List[NormalizedFareObservation] = []
    seen_offers: Dict[str, str] = {} # offer_fingerprint -> duplicate_group_id

    for r in records:
        norm_obs = normalize_record(r)
        if norm_obs is not None:
            fp = norm_obs.offer_fingerprint
            if fp in seen_offers:
                norm_obs.duplicate_group_id = seen_offers[fp]
                norm_obs.quality_status = "DUPLICATE"
            else:
                dup_id = f"dup_{fp[:12]}"
                seen_offers[fp] = dup_id
                norm_obs.duplicate_group_id = None
                
            normalized_list.append(norm_obs)
            
    return normalized_list
