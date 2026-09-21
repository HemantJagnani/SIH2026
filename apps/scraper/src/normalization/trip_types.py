"""
Trip Type normalizer.

Uses pre-defined dictionary mapping since trip type sets are very small.
"""

import re

from models.enums import TripType
from normalization.core import NormalizationException, NormalizationResult


TRIP_MAP = {
    "oneway": TripType.ONE_WAY,
    "one way": TripType.ONE_WAY,
    "one-way": TripType.ONE_WAY,
    "ow": TripType.ONE_WAY,
    "roundtrip": TripType.ROUND_TRIP,
    "round trip": TripType.ROUND_TRIP,
    "round-trip": TripType.ROUND_TRIP,
    "rt": TripType.ROUND_TRIP,
    "return": TripType.ROUND_TRIP,
}


def normalize_trip_type(raw_trip_type: str, field_name: str = "trip_type") -> NormalizationResult[TripType]:
    if not raw_trip_type or not raw_trip_type.strip():
        raise NormalizationException(field_name, raw_trip_type, "Empty trip type string")

    # Remove extra spaces and make lower
    cleaned = re.sub(r'\s+', ' ', raw_trip_type.strip().lower())
    
    if cleaned in TRIP_MAP:
        return NormalizationResult(
            raw_value=raw_trip_type,
            normalized_value=TRIP_MAP[cleaned],
            is_success=True,
            confidence=1.0,
        )

    raise NormalizationException(field_name, raw_trip_type, f"Unknown trip type variant: {cleaned}")
