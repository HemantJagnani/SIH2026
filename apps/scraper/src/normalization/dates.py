"""
Date and time normalizers.

Handles parsing of ISO strings, custom formats, and adding timezone awareness.
"""

from datetime import date, datetime, timezone, timedelta
from typing import overload

from normalization.core import NormalizationException, NormalizationResult


IST_OFFSET = timedelta(hours=5, minutes=30)
IST_TZ = timezone(IST_OFFSET, name="IST")


def normalize_travel_date(raw_date: str, field_name: str = "travel_date") -> NormalizationResult[date]:
    """
    Deterministically parses a travel date string into a datetime.date object.
    Supports ISO format (YYYY-MM-DD).
    
    Args:
        raw_date: e.g. "2026-09-21"
        field_name: The field being parsed
        
    Raises:
        NormalizationException on failure.
    """
    if not raw_date or not raw_date.strip():
        raise NormalizationException(field_name, raw_date, "Empty date string")

    cleaned = raw_date.strip()
    
    try:
        # We enforce YYYY-MM-DD standard format initially
        parsed = date.fromisoformat(cleaned[:10])  # slice to ignore time if passed
        return NormalizationResult(
            raw_value=raw_date,
            normalized_value=parsed,
            is_success=True,
            confidence=1.0,
        )
    except ValueError:
        raise NormalizationException(field_name, raw_date, "Failed to parse date; expected YYYY-MM-DD")


def normalize_timestamp(
    raw_timestamp: str, 
    field_name: str = "timestamp", 
    assume_ist: bool = True
) -> NormalizationResult[datetime]:
    """
    Parses a timestamp and ensures it is timezone-aware.
    If assume_ist is True and the string has no tz info, it assumes IST.
    """
    if not raw_timestamp or not raw_timestamp.strip():
        raise NormalizationException(field_name, raw_timestamp, "Empty timestamp string")

    cleaned = raw_timestamp.strip()

    try:
        # Handles most standard ISO-8601 strings
        parsed = datetime.fromisoformat(cleaned)
        
        if parsed.tzinfo is None:
            if assume_ist:
                parsed = parsed.replace(tzinfo=IST_TZ)
            else:
                parsed = parsed.replace(tzinfo=timezone.utc)
                
        return NormalizationResult(
            raw_value=raw_timestamp,
            normalized_value=parsed,
            is_success=True,
            confidence=1.0,
        )
    except ValueError:
        raise NormalizationException(field_name, raw_timestamp, "Failed to parse timestamp")
