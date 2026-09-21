import pytest
from datetime import date
import uuid
from decimal import Decimal

from adapters.ignav import IgnavAdapter
from adapters.models import FareSearchRequest
from models.enums import TripType, CabinClass

@pytest.fixture
def mock_ignav_response():
    return {
        "origin": "DEL",
        "destination": "BOM",
        "departure_date": "2026-10-08",
        "itineraries": [
            {
                "price": {
                    "amount": 75.50,
                    "currency": "INR",
                    "status": "verified"
                },
                "outbound": {
                    "segments": [
                        {
                            "marketing_carrier_code": "6E",
                            "flight_number": "123",
                            "operating_carrier_name": "IndiGo",
                            "departure_airport": "DEL",
                            "departure_time_local": "2026-10-08T10:00:00",
                            "departure_time_utc": "2026-10-08T04:30:00Z",
                            "arrival_airport": "BOM",
                            "arrival_time_local": "2026-10-08T12:00:00",
                            "arrival_time_utc": "2026-10-08T06:30:00Z",
                            "duration_minutes": 120,
                            "aircraft": "320"
                        }
                    ]
                },
                "cabin_class": "economy",
                "ignav_id": "itin_12345",
                "requires_self_transfer": False
            }
        ]
    }

@pytest.fixture
def search_request():
    return FareSearchRequest(
        request_id=uuid.uuid4(),
        source="ignav",
        origin="DEL",
        destination="BOM",
        travel_date=date(2026, 10, 8),
        lead_days=7,
        trip_type=TripType.ONE_WAY,
        cabin=CabinClass.ECONOMY,
        adults=1,
        children=0,
        infants=0,
        currency="INR",
        collection_mode="API"
    )

def test_ignav_adapter_parse(mock_ignav_response, search_request):
    adapter = IgnavAdapter()
    
    observations = adapter._parse(mock_ignav_response, search_request)
    
    assert len(observations) == 1
    obs = observations[0]
    
    assert obs.airline == "IndiGo"
    assert obs.airline_code == "6E"
    assert obs.flight_number == "6E 123"
    assert obs.stops == 0
    
    assert float(obs.total_fare) == 75.50
    assert obs.currency == "INR"
    assert obs.price_status == "verified"
    
    assert obs.base_fare is None
    assert obs.taxes is None
    
    assert obs.source_itinerary_id == "itin_12345"
    assert obs.requires_self_transfer is False
    
    assert obs.departure_time_local.isoformat() == "2026-10-08T10:00:00"
    assert obs.departure_time_utc.isoformat() == "2026-10-08T04:30:00+00:00"
