"""
Fingerprint calculation for flight itineraries, commercial offers, and cross-source canonical offers.
Implements §9 of the APIx Cross-Source Specification.
"""

from __future__ import annotations

import hashlib
import re
from typing import Optional


def normalize_flight_number(raw_flight_num: Optional[str]) -> str:
    """
    Normalizes flight numbers across sources:
    e.g. '6E 204', '6E-204', '6e204' -> '6E204'
    e.g. 'AI 805', 'AI-805' -> 'AI805'
    """
    if not raw_flight_num:
        return "UNKNOWN_FLIGHT"
    cleaned = re.sub(r"[\s\-_]", "", str(raw_flight_num)).upper()
    return cleaned if cleaned else "UNKNOWN_FLIGHT"


def normalize_time_str(time_val: Optional[str]) -> str:
    """
    Normalizes departure/arrival time strings:
    e.g. '2026-10-04T10:00:00' -> '10:00'
    e.g. '10:00:00' -> '10:00'
    e.g. '10:00' -> '10:00'
    """
    if not time_val or time_val in ("UNKNOWN", "NOT_PROVIDED"):
        return "UNKNOWN_TIME"
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
    travel_date: str,
    airline: str,
    flight_number: str,
    departure_time: str,
) -> str:
    """
    Computes a deterministic hash for a physical flight itinerary.
    Represents the physical transport service regardless of fare tier or source.
    """
    norm_origin = origin.strip().upper()
    norm_dest = destination.strip().upper()
    norm_date = travel_date.strip()
    norm_airline = re.sub(r"[\s\-_]", "", airline.strip()).upper()
    norm_fn = normalize_flight_number(flight_number)
    norm_dep = normalize_time_str(departure_time)

    canonical_key = f"{norm_origin}|{norm_dest}|{norm_date}|{norm_airline}|{norm_fn}|{norm_dep}"
    return hashlib.sha256(canonical_key.encode("utf-8")).hexdigest()[:16]


def compute_offer_fingerprint(
    itinerary_fp: str,
    cabin: str = "ECONOMY",
    fare_family: str = "NOT_PROVIDED",
    baggage: str = "NOT_PROVIDED",
    refundability: str = "UNKNOWN",
    passenger_type: str = "ADULT",
) -> str:
    """
    Computes a deterministic hash for a commercial offer on an itinerary.
    Distinguishes fare families and conditions on the same physical flight.
    """
    norm_cabin = cabin.strip().upper()
    norm_ff = fare_family.strip().upper()
    norm_bag = baggage.strip().upper()
    norm_ref = refundability.strip().upper()
    norm_pax = passenger_type.strip().upper()

    canonical_key = f"{itinerary_fp}|{norm_cabin}|{norm_ff}|{norm_bag}|{norm_ref}|{norm_pax}"
    return hashlib.sha256(canonical_key.encode("utf-8")).hexdigest()[:16]


def compute_canonical_offer_fingerprint(
    route: str,
    travel_date: str,
    airline: str,
    flight_number: str,
    departure_time: str,
    stops: int = 0,
    cabin: str = "ECONOMY",
    fare_family: str = "NOT_PROVIDED",
    baggage: str = "NOT_PROVIDED",
    refundability: str = "UNKNOWN",
    passenger_type: str = "ADULT",
) -> str:
    """
    Computes universal cross-source canonical identity.
    Used for deterministically identifying identical product offers across aggregators.
    Does NOT depend on price so price differences on the same offer are detected.
    """
    norm_route = route.strip().upper()
    norm_date = travel_date.strip()
    norm_airline = re.sub(r"[\s\-_]", "", airline.strip()).upper()
    norm_fn = normalize_flight_number(flight_number)
    norm_dep = normalize_time_str(departure_time)
    norm_stops = str(stops)
    norm_cabin = cabin.strip().upper()
    norm_ff = fare_family.strip().upper()
    norm_bag = baggage.strip().upper()
    norm_ref = refundability.strip().upper()
    norm_pax = passenger_type.strip().upper()

    canonical_key = (
        f"{norm_route}|{norm_date}|{norm_airline}|{norm_fn}|{norm_dep}|"
        f"{norm_stops}|{norm_cabin}|{norm_ff}|{norm_bag}|{norm_ref}|{norm_pax}"
    )
    return hashlib.sha256(canonical_key.encode("utf-8")).hexdigest()[:24]
