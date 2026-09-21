"""
Shared test fixtures for validation tests.
"""
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

import pytest

from models.enums import AvailabilityStatus, CabinClass, TripType
from models.version import SCHEMA_VERSION

VALID_COLLECTED_AT = datetime(2026, 9, 21, 10, 0, 0, tzinfo=timezone.utc)
VALID_TRAVEL_DATE_STR = "2026-09-28"  # 7 days ahead

def make_valid_payload(**overrides) -> dict:
    """Build a minimal valid FareObservation payload."""
    base = {
        "collection_run_id": str(uuid.uuid4()),
        "source": "indigo",
        "collected_at": VALID_COLLECTED_AT,
        "travel_date": "2026-09-28",
        "lead_days": 7,
        "origin": "DEL",
        "destination": "BOM",
        "airline": "IndiGo",
        "trip_type": TripType.ONE_WAY,
        "cabin": CabinClass.ECONOMY,
        "passenger_count": 1,
        "availability": AvailabilityStatus.AVAILABLE,
        "currency": "INR",
        "total_fare": Decimal("5240.00"),
        "adapter_version": "1.0.0",
        "normalizer_version": "1.0.0",
        "schema_version": SCHEMA_VERSION,
    }
    base.update(overrides)
    return base
