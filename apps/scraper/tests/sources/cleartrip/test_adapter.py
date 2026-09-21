import os
import sys
from datetime import date
from decimal import Decimal
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src')))

from adapters.models import FareSearchRequest, CollectionMode, CollectionStatus
from models.observation import TripType, CabinClass, AvailabilityStatus
from sources.cleartrip.adapter import CleartripFlightApiAdapter

@pytest.fixture
def search_request():
    return FareSearchRequest(
        source="cleartrip",
        origin="DEL",
        destination="BOM",
        travel_date=date(2026, 9, 28),
        lead_days=7,
        trip_type=TripType.ONE_WAY,
        cabin=CabinClass.ECONOMY,
        adults=1,
        currency="INR",
        collection_mode=CollectionMode.API
    )

@pytest.mark.asyncio
async def test_cleartrip_adapter(search_request):
    # Initialize adapter with mock=True
    adapter = CleartripFlightApiAdapter(use_mock=True)
    
    # Run collection
    result = await adapter.collect(search_request)
    
    # Verify overall result
    assert result.status == CollectionStatus.SUCCESS
    assert len(result.observations) == 2
    assert result.http_status == 200
    
    # Verify first observation (AVAILABLE)
    obs1 = result.observations[0]
    assert obs1.source == "cleartrip"
    assert obs1.origin == "DEL"
    assert obs1.destination == "BOM"
    assert obs1.airline == "Indigo"
    assert obs1.flight_number == "6E-5001"
    assert obs1.base_fare == Decimal("3500.00")
    assert obs1.taxes == Decimal("1240.00")
    assert obs1.total_fare == Decimal("4740.00")
    assert obs1.availability == AvailabilityStatus.AVAILABLE
    
    # Verify second observation (SOLD_OUT)
    obs2 = result.observations[1]
    assert obs2.airline == "Air India"
    assert obs2.flight_number == "AI-805"
    assert obs2.base_fare == Decimal("4200.00")
    assert obs2.total_fare == Decimal("5550.00")
    assert obs2.availability == AvailabilityStatus.SOLD_OUT
