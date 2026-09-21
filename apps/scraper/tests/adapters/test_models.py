import os
import sys
from datetime import date
from pydantic import ValidationError
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

from adapters.models import CollectionMode, FareSearchRequest
from models.observation import CabinClass, TripType


def test_fare_search_request_valid():
    request = FareSearchRequest(
        source="test_source",
        origin="DEL",
        destination="BOM",
        travel_date=date(2026, 9, 21),
        lead_days=1,
        collection_mode=CollectionMode.API
    )
    assert request.source == "test_source"
    assert request.origin == "DEL"
    assert request.destination == "BOM"
    assert request.adults == 1
    assert request.children == 0
    assert request.infants == 0
    assert request.currency == "INR"
    assert request.trip_type == TripType.ONE_WAY
    assert request.cabin == CabinClass.ECONOMY


def test_fare_search_request_same_origin_dest_fails():
    with pytest.raises(ValidationError) as exc_info:
        FareSearchRequest(
            source="test_source",
            origin="DEL",
            destination="DEL",
            travel_date=date(2026, 9, 21),
            lead_days=1,
            collection_mode=CollectionMode.API
        )
    assert "Origin and destination cannot be the same" in str(exc_info.value)


def test_fare_search_request_invalid_iata_fails():
    with pytest.raises(ValidationError):
        FareSearchRequest(
            source="test_source",
            origin="DE",  # Too short
            destination="BOMB", # Too long
            travel_date=date(2026, 9, 21),
            lead_days=1,
            collection_mode=CollectionMode.API
        )


def test_fare_search_request_frozen():
    request = FareSearchRequest(
        source="test_source",
        origin="DEL",
        destination="BOM",
        travel_date=date(2026, 9, 21),
        lead_days=1,
        collection_mode=CollectionMode.API
    )
    with pytest.raises(ValidationError):
        request.adults = 2
