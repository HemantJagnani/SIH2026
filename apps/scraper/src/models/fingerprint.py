"""
Deterministic fingerprinting utilities for APIx Phase 2.
Implements ItineraryFingerprint and OfferFingerprint per Methodology §15.1, §15.2.
"""

from __future__ import annotations
import hashlib
from datetime import date, datetime
from typing import Any, Optional


def normalize_string(val: Optional[str]) -> str:
    """Normalize string for consistent hashing: strip whitespace and uppercase."""
    if val is None:
        return ""
    return str(val).strip().upper()


def format_time_for_hash(time_val: Optional[datetime | str]) -> str:
    """Format datetime or time string into standard HH:MM representation."""
    if time_val is None:
        return "UNKNOWN_TIME"
    if isinstance(time_val, datetime):
        return time_val.strftime("%H:%M")
    # If string like "05:45:00" or "05:45"
    s = str(time_val).strip()
    if "T" in s:
        s = s.split("T")[-1]
    parts = s.split(":")
    if len(parts) >= 2:
        return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}"
    return s.upper()


def compute_itinerary_fingerprint(
    origin: str,
    destination: str,
    travel_date: date | str,
    airline: str,
    flight_number: str,
    departure_time: Optional[datetime | str] = None,
    arrival_time: Optional[datetime | str] = None,
    stops: Optional[int] = 0,
) -> str:
    """
    Computes deterministic ItineraryFingerprint (F_itinerary) per Methodology §15.1.
    
    F_itinerary = hash(
        origin, destination, travel_date, airline,
        flight_number, departure, arrival, stops
    )
    """
    norm_origin = normalize_string(origin)
    norm_dest = normalize_string(destination)
    norm_date = travel_date.isoformat() if isinstance(travel_date, date) else str(travel_date).strip()
    norm_airline = normalize_string(airline)
    norm_flight = normalize_string(flight_number)
    norm_dep = format_time_for_hash(departure_time)
    norm_arr = format_time_for_hash(arrival_time)
    norm_stops = str(stops) if stops is not None else "0"

    canonical_representation = (
        f"{norm_origin}|{norm_dest}|{norm_date}|{norm_airline}|"
        f"{norm_flight}|{norm_dep}|{norm_arr}|{norm_stops}"
    )

    return hashlib.sha256(canonical_representation.encode("utf-8")).hexdigest()


def compute_offer_fingerprint(
    itinerary_fingerprint: str,
    fare_family: Optional[str] = "STANDARD",
    cabin: Optional[str] = "ECONOMY",
    baggage: Optional[str] = "STANDARD",
    refundability: Optional[str] = "UNKNOWN",
    changeability: Optional[str] = "UNKNOWN",
) -> str:
    """
    Computes deterministic OfferFingerprint (F_offer) per Methodology §15.2.
    
    F_offer = hash(
        F_itinerary, fare_family, cabin, baggage,
        refundability, changeability
    )
    """
    norm_itin = normalize_string(itinerary_fingerprint)
    norm_fare_fam = normalize_string(fare_family) or "STANDARD"
    norm_cabin = normalize_string(cabin) or "ECONOMY"
    norm_baggage = normalize_string(baggage) or "STANDARD"
    norm_ref = normalize_string(refundability) or "UNKNOWN"
    norm_chg = normalize_string(changeability) or "UNKNOWN"

    canonical_representation = (
        f"{norm_itin}|{norm_fare_fam}|{norm_cabin}|{norm_baggage}|"
        f"{norm_ref}|{norm_chg}"
    )

    return hashlib.sha256(canonical_representation.encode("utf-8")).hexdigest()
