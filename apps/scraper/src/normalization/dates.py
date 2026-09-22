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


import re

_TIME_RE = re.compile(r"(\d{1,2}):(\d{2})\s*(AM|PM)?", re.IGNORECASE)

def normalize_time_local(
    time_str: str, 
    travel_date: date,
    field_name: str = "time_local",
) -> NormalizationResult[datetime]:
    """
    Parses a flight time string (e.g. "06:30", "6:30 AM") into a datetime
    in the local IST timezone, combined with the given travel_date.
    """
    if not time_str or not time_str.strip():
        raise NormalizationException(field_name, time_str, "Empty time string")

    time_str = time_str.strip()
    match = _TIME_RE.search(time_str)
    if not match:
        raise NormalizationException(field_name, time_str, "Could not parse time string format")

    hour, minute = int(match.group(1)), int(match.group(2))
    ampm = (match.group(3) or "").upper()

    if ampm == "PM" and hour != 12:
        hour += 12
    elif ampm == "AM" and hour == 12:
        hour = 0

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise NormalizationException(field_name, time_str, f"Time out of range h={hour} m={minute}")

    try:
        dt = datetime(
            travel_date.year, travel_date.month, travel_date.day,
            hour, minute, 0,
            tzinfo=IST_TZ,
        )
        return NormalizationResult(
            raw_value=time_str,
            normalized_value=dt,
            is_success=True,
            confidence=1.0,
        )
    except ValueError as exc:
        raise NormalizationException(field_name, time_str, f"Datetime construction failed: {exc}")


def to_utc(local_dt: datetime) -> datetime:
    """
    Convert a timezone-aware local datetime to UTC.
    If local_dt has no tzinfo, assumes IST.
    """
    if local_dt.tzinfo is None:
        local_dt = local_dt.replace(tzinfo=IST_TZ)
    return local_dt.astimezone(timezone.utc)

