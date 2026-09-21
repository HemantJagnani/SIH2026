"""
Unit tests for the Cleartrip Source Adapter.
"""
import sys
import os
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
import json

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

from adapters.cleartrip import CleartripAdapter
from adapters.models import FareSearchRequest, CollectionStatus
from models.enums import TripType, CabinClass, AvailabilityStatus

# Mock data based on Cleartrip API documentation
MOCK_RESPONSE = {
  "id": "631787344cedfd0007bbdc10",
  "success": True,
  "count": {
    "adult": 1,
    "child": 0,
    "infant": 0
  },
  "origin": {
    "code": "DEL",
    "id": 1,
    "airport": "Indira Gandhi International Airport",
    "city": "Delhi",
    "country": "INDIA"
  },
  "destination": {
    "code": "BOM",
    "id": 2,
    "airport": "Chhatrapati Shivaji International Airport",
    "city": "Mumbai",
    "country": "INDIA"
  },
  "results": [
    {
      "remaining": 9,
      "details": {
        "arrival": 1665553500000,
        "departure": 1665545400000,
        "numberOfStops": 0,
        "duration": 135
      },
      "key": "AI|678|1665545400000|1665553500000",
      "fares": [
        {
          "override": False,
          "appId": "63039e1f46e0fb0007c7dbe9",
          "key": "15-2-10-8966528749_104DELBOMAI678_279017526829771",
          "type": "REGULAR",
          "typeKey": "PUBLISHED",
          "adult": {
            "baggage": {
              "checkIn": "25 Kg (01 Piece only)",
              "cabin": "7 Kg"
            },
            "cancellationCharges": {
              "type": "REFUNDABLE"
            },
            "ancillery": {
              "meal": False,
              "seat": False,
              "dateChange": False
            },
            "remainingSeats": 9,
            "offeredFare": 6225.3,
            "publishedFare": 6514,
            "comission": 288.7,
            "bookingClass": "U",
            "baseFare": 5130,
            "taxes": {
              "total": 1384,
              "breakups": {
                "Carrier Misc": 170,
                "Fuel Surcharge": 0,
                "Management Fee Tax": 9,
                "Other Charges": 890,
                "Management Fees": 50,
                "Gst Charges": 265
              }
            }
          }
        }
      ],
      "segments": [
        {
          "flightCode": "AI",
          "airline": "Air India",
          "rank": 0,
          "flightNumber": "678",
          "durationInMin": 135,
          "departure": {
            "code": "DEL",
            "airport": "Delhi Indira Gandhi Intl",
            "city": "Delhi",
            "country": "India"
          },
          "departureTime": 1665545400000,
          "departureDate": "2022-10-12T09:00",
          "arrival": {
            "code": "BOM",
            "airport": "Chhatrapati Shivaji",
            "city": "Mumbai",
            "country": "India"
          },
          "arrivalTime": 1665553500000,
          "arrrivalDate": "2022-10-12T11:15"
        }
      ],
      "operator": {
        "name": "Air India",
        "code": "AI",
        "lcc": False,
        "number": "678",
        "equipment": "32N"
      }
    }
  ]
}

@pytest.fixture
def sample_request():
    return FareSearchRequest(
        request_id=uuid.uuid4(),
        source="cleartrip",
        origin="DEL",
        destination="BOM",
        travel_date=date(2030, 10, 12),
        lead_days=7,
        trip_type=TripType.ONE_WAY,
        cabin=CabinClass.ECONOMY,
        adults=1,
        children=0,
        infants=0,
        currency="INR",
        collection_mode="API"
    )

def test_cleartrip_parser(sample_request):
    adapter = CleartripAdapter()
    
    observations = adapter._parse(MOCK_RESPONSE, sample_request)
    
    assert len(observations) == 1
    obs = observations[0]
    
    assert obs.source == "cleartrip"
    assert obs.origin == "DEL"
    assert obs.destination == "BOM"
    assert obs.airline == "Air India"
    assert obs.airline_code == "AI"
    assert obs.flight_number == "AI 678"
    assert obs.base_fare == Decimal("5130")
    assert obs.taxes == Decimal("1384")
    assert obs.total_fare == Decimal("6225.3")
    assert obs.availability == AvailabilityStatus.AVAILABLE
    assert obs.fare_class == "U"
    assert obs.fare_family == "PUBLISHED"
    assert obs.stops == 0

    # test dates
    assert obs.departure_time == datetime.fromtimestamp(1665545400000 / 1000, tz=timezone.utc)
    assert obs.arrival_time == datetime.fromtimestamp(1665553500000 / 1000, tz=timezone.utc)
