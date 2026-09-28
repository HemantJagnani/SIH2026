import pytest
import uuid
from datetime import date
from bs4 import BeautifulSoup

from models.request import FareSearchRequest, PassengerCount
from models.enums import CabinClass, TripType
from sources.googleflights.url_builder import GoogleFlightsUrlBuilder
from sources.googleflights.parser import parse_dom, parse_expanded_cards, _extract_flight_data

@pytest.fixture
def mock_request():
    return FareSearchRequest(
        origin="DEL",
        destination="BOM",
        travel_date=date(2026, 9, 30),
        trip_type=TripType.ONE_WAY,
        cabin=CabinClass.ECONOMY,
        source="google_flights",
        collection_mode="BROWSER",
        lead_days=7
    )

def test_url_builder(mock_request):
    url = GoogleFlightsUrlBuilder.build_url(mock_request)
    assert "https://www.google.com/travel/flights" in url
    assert "DEL" in url
    assert "BOM" in url
    assert "2026-09-30" in url
    assert "oneway" in url
    assert "curr=INR" in url

def test_url_builder_gau_destination_resolution_del_gau():
    """
    Regression test: DEL -> GAU must construct a valid Google Flights query with
    'Guwahati' rather than bare 'GAU' to prevent Google Flights Explore page fallback.
    """
    req = FareSearchRequest(
        origin="DEL",
        destination="GAU",
        travel_date=date(2026, 10, 5),
        trip_type=TripType.ONE_WAY,
        cabin=CabinClass.ECONOMY,
        source="google_flights",
        collection_mode="BROWSER",
        lead_days=7
    )
    url = GoogleFlightsUrlBuilder.build_url(req)
    assert "https://www.google.com/travel/flights" in url
    assert "curr=INR" in url
    assert "oneway" in url
    assert "DEL" in url
    
    # Crucial: Query must resolve destination to 'Guwahati', NOT bare 'GAU'
    assert "Guwahati" in url
    assert "Flights+to+Guwahati+from+DEL" in url
    assert "Flights+to+GAU+from" not in url

def test_url_builder_gau_destination_resolution_blr_gau():
    """
    Regression test: BLR -> GAU must construct a valid Google Flights query with
    'Guwahati' rather than bare 'GAU'.
    """
    req = FareSearchRequest(
        origin="BLR",
        destination="GAU",
        travel_date=date(2026, 10, 5),
        trip_type=TripType.ONE_WAY,
        cabin=CabinClass.ECONOMY,
        source="google_flights",
        collection_mode="BROWSER",
        lead_days=7
    )
    url = GoogleFlightsUrlBuilder.build_url(req)
    assert "https://www.google.com/travel/flights" in url
    assert "curr=INR" in url
    assert "oneway" in url
    assert "BLR" in url
    
    # Crucial: Query must resolve destination to 'Guwahati', NOT bare 'GAU'
    assert "Guwahati" in url
    assert "Flights+to+Guwahati+from+BLR" in url
    assert "Flights+to+GAU+from" not in url

def test_url_builder_resolve_destination_method():
    """Test resolve_destination unit behavior across standard and mapped codes."""
    assert GoogleFlightsUrlBuilder.resolve_destination("GAU") == "Guwahati"
    assert GoogleFlightsUrlBuilder.resolve_destination("gau") == "Guwahati"
    assert GoogleFlightsUrlBuilder.resolve_destination(" GAU ") == "Guwahati"
    assert GoogleFlightsUrlBuilder.resolve_destination("BOM") == "BOM"
    assert GoogleFlightsUrlBuilder.resolve_destination("DEL") == "DEL"
    assert GoogleFlightsUrlBuilder.resolve_destination("BLR") == "BLR"

def test_parser_normal_results(mock_request):
    run_id = uuid.uuid4()
    # A mock DOM representing Google Flights structural response
    html = """
    <ul>
        <li>
            Air India | 07:00 AM – 09:15 AM | 2 hr 15 min | DEL–BOM | Non-stop | ₹5,450
        </li>
        <li>
            IndiGo | 08:30 AM – 10:45 AM | 2 hr 15 min | DEL–BOM | 1 stop | ₹4,200
        </li>
    </ul>
    """
    fares = parse_dom(html, mock_request, run_id, "google_flights")
    assert len(fares) == 2
    
    fare1 = fares[0]
    assert fare1["airline"] == "Air India"
    assert fare1["total_fare"] == 5450.0
    assert fare1["stops"] == 0
    assert fare1["price_raw_text"] == "₹5,450"
    assert "07:00:00" in fare1["departure_time_local"]
    
    fare2 = fares[1]
    assert fare2["airline"] == "IndiGo"
    assert fare2["total_fare"] == 4200.0
    assert fare2["stops"] == 1

def test_parser_malformed_price(mock_request):
    run_id = uuid.uuid4()
    html = """
    <ul>
        <li>
            Air India | 07:00 AM – 09:15 AM | 2 hr 15 min | DEL–BOM | Non-stop | Price Unavailable
        </li>
    </ul>
    """
    fares = parse_dom(html, mock_request, run_id, "google_flights")
    assert len(fares) == 0

def test_parser_no_results(mock_request):
    run_id = uuid.uuid4()
    html = "<div>No matching flights found</div>"
    fares = parse_dom(html, mock_request, run_id, "google_flights")
    assert len(fares) == 0

def test_parse_expanded_cards(mock_request):
    run_id = uuid.uuid4()
    html1 = """
    <li>
        Air India | 07:00 AM – 09:15 AM | 2 hr 15 min | DEL–BOM | Non-stop | ₹5,450
        <div>
            <div><span>Flight</span></div>
            <span>AI 123</span>
            <span>Carry-on included (7 kg)</span>
            <span>Checked baggage included (15 kg)</span>
        </div>
    </li>
    """
    fares = parse_expanded_cards([html1], mock_request, run_id, "google_flights")
    assert len(fares) == 1
    
    fare = fares[0]
    assert fare["airline"] == "Air India"
    assert fare["total_fare"] == 5450.0
    assert fare["stops"] == 0
    assert fare["cabin_baggage_kg"] == 7
    assert fare["checkin_baggage_kg"] == 15
    assert len(fare["flight_segments"]) == 1
    assert fare["flight_segments"][0]["flight_number"] == "AI-123"

def test_parse_expanded_cards_no_fabrication_when_unspecified(mock_request):
    run_id = uuid.uuid4()
    # When kg is not explicitly stated, baggage values MUST be None (no fabrication)
    html_no_kg = """
    <li>
        IndiGo | 08:00 AM – 10:15 AM | 2 hr 15 min | DEL–BOM | Non-stop | ₹4,999
        <div>
            <span>Carry-on included</span>
            <span>Checked baggage</span>
        </div>
    </li>
    """
    fares = parse_expanded_cards([html_no_kg], mock_request, run_id, "google_flights")
    assert len(fares) == 1
    fare = fares[0]
    assert fare["cabin_baggage_kg"] is None
    assert fare["checkin_baggage_kg"] is None
    assert fare["base_fare"] is None
    assert fare["taxes"] is None
    assert fare["gst"] is None

