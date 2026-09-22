import os
import uuid
from datetime import date
from pathlib import Path

import pytest

from models.request import FareSearchRequest
from models.enums import TripType, CabinClass
from sources.easemytrip.parser import parse_dom

def test_easemytrip_parser_real_capture():
    """Test the EaseMyTrip DOM parser against the real browser capture."""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "easemytrip" / "del_bom_results.html"
    
    if not fixture_path.exists():
        pytest.skip("Fixture del_bom_results.html not found.")
        
    with open(fixture_path, "r", encoding="utf-8") as f:
        html_content = f.read()
        
    request = FareSearchRequest(
        source="easemytrip",
        collection_mode="BROWSER",
        origin="DEL",
        destination="BOM",
        travel_date=date(2026, 9, 29),
        lead_days=7,
        passenger_count={"adults": 1, "children": 0, "infants": 0},
        cabin=CabinClass.ECONOMY,
        trip_type=TripType.ONE_WAY
    )
    
    run_id = uuid.uuid4()
    
    observations = parse_dom(html_content, request, run_id, "easemytrip")
    
    # Assert we extracted the expected 145 cards
    assert len(observations) == 145
    
    # Assert on the first observation
    first_obs = observations[0]
    
    # Verify core fields
    assert first_obs.source == "easemytrip"
    assert first_obs.origin == "DEL"
    assert first_obs.destination == "BOM"
    
    # Verify we extracted real data, not placeholders
    assert first_obs.airline != "UNKNOWN"
    assert first_obs.airline is not None
    assert first_obs.flight_number != "UNKNOWN"
    assert first_obs.flight_number is not None
    assert first_obs.total_fare > 0
    assert first_obs.total_fare is not None
    
    # Verify stops was parsed correctly
    assert first_obs.stops is not None
    assert isinstance(first_obs.stops, int)
    
    # Ensure source_offer_id is generated
    assert first_obs.source_offer_id is not None
    assert first_obs.source_offer_id.startswith("emt-")
    
    # Ensure the parser doesn't invent unknown fields like base_fare or taxes
    # By default, they should be None in FareObservation
    assert getattr(first_obs, 'base_fare', None) is None
    assert getattr(first_obs, 'total_tax', None) is None
    
    # Make sure we didn't use Angular attributes by verifying the length is correct 
    # (if the selector was wrong, length wouldn't be exactly 145)
    assert len(observations) == 145
