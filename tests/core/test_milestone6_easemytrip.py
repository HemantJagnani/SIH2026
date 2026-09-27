import pytest
from uuid import uuid4
from datetime import date, timedelta
from models.request import FareSearchRequest
from models.observation import FareObservation
from sources.easemytrip.adapter import EaseMyTripAdapter
from sources.easemytrip.navigation import NavigationState

@pytest.fixture
def dummy_request():
    today = date.today()
    return FareSearchRequest(
        source="easemytrip",
        collection_mode="BROWSER",
        origin="DEL",
        destination="BOM",
        travel_date=today + timedelta(days=7),
        lead_days=7,
        passenger_count={"adults": 1, "children": 0, "infants": 0},
        cabin="ECONOMY",
        trip_type="ONE_WAY",
        market="IN"
    )

@pytest.mark.asyncio
async def test_easemytrip_captcha_detected(dummy_request):
    """Test that a CAPTCHA correctly terminates and does not produce observations."""
    adapter = EaseMyTripAdapter()
    
    # We mock the navigation execute to return CAPTCHA_DETECTED
    class MockNavigation:
        def __init__(self, *args, **kwargs):
            pass
        async def execute(self):
            from sources.easemytrip.navigation import SearchResultContext
            ctx = SearchResultContext()
            ctx.terminal_state = NavigationState.CAPTCHA_DETECTED
            return ctx
            
    import sources.easemytrip.adapter as adapter_module
    original_nav = adapter_module.EaseMyTripNavigation
    adapter_module.EaseMyTripNavigation = MockNavigation
    
    # Also mock capture_evidence so we don't write files during tests
    async def mock_capture(*args, **kwargs):
        pass
    adapter_module.capture_evidence = mock_capture
    
    try:
        observations, state = await adapter.search(None, dummy_request, uuid4())
        assert len(observations) == 0
    finally:
        adapter_module.EaseMyTripNavigation = original_nav

@pytest.mark.asyncio
async def test_easemytrip_valid_response(dummy_request):
    """Test parsing a valid network response."""
    adapter = EaseMyTripAdapter()
    
    class MockNavigation:
        def __init__(self, *args, **kwargs):
            pass
        async def execute(self):
            from sources.easemytrip.navigation import SearchResultContext
            ctx = SearchResultContext()
            ctx.terminal_state = NavigationState.RESULTS_DETECTED
            ctx.rendered_dom = "<html><body><div class='row'>flight</div></body></html>"
            # Mock JSON response
            ctx.network_response = {
                "flights": [
                    {"flightNo": "6E-123", "price": 5000, "currency": "INR"}
                ]
            }
            return ctx
            
    import sources.easemytrip.adapter as adapter_module
    original_nav = adapter_module.EaseMyTripNavigation
    adapter_module.EaseMyTripNavigation = MockNavigation
    
    # Mock parser since we test the adapter flow
    def mock_parser(*args, **kwargs):
        from decimal import Decimal
        from datetime import datetime, timezone
        from models.observation import AvailabilityStatus, CabinClass, TripType
        return [
            FareObservation(
                collection_run_id=uuid4(),
                source="easemytrip",
                origin="DEL",
                destination="BOM",
                travel_date=dummy_request.travel_date,
                lead_days=dummy_request.lead_days,
                collected_at=datetime.now(timezone.utc),
                airline="6E",
                trip_type=TripType.ONE_WAY,
                cabin=CabinClass.ECONOMY,
                passenger_count=1,
                availability=AvailabilityStatus.AVAILABLE,
                adapter_version="1.0.0",
                normalizer_version="1.0.0",
                flight_number="123",
                total_fare=Decimal("5000"),
                currency="INR",
                source_url="http://example.com",
                source_offer_id="mock-offer"
            )
        ]
    
    import sources.easemytrip.adapter as adapter_pkg
    original_parse_dom = adapter_pkg.parse_dom
    adapter_pkg.parse_dom = mock_parser
    
    try:
        observations, state = await adapter.search(None, dummy_request, uuid4())
        assert len(observations) == 1
        assert observations[0].total_fare == 5000
    finally:
        adapter_module.EaseMyTripNavigation = original_nav
        adapter_pkg.parse_dom = original_parse_dom
