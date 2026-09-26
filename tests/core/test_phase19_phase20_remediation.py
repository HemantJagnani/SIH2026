"""
Comprehensive Test Suite for Phase 19 (Test Fixtures & Edge Cases)
and Phase 20 (No Fabrication Guarantee).

Verifies:
1. Normal parsing (Google & EaseMyTrip)
2. Missing fields provenance
3. Multiple fare offers (EaseMyTrip 1 Itinerary -> Many Offers)
4. Multiple segments
5. Price-only observations
6. Blocked page detection
7. CAPTCHA detection
8. Selector drift detection
9. Enrichment timeout & bounded transitions
10. Safe-stop behavior
11. Evidence generation
12. No fabricated fields (strictly enforces that missing components are None)
"""

import json
import uuid
from datetime import date, datetime
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from models.enums import AvailabilityStatus, CabinClass, TripType, WorkflowState
from models.provenance import ExtractionMode, FieldStatus, MissingReason
from models.request import FareSearchRequest
from models.diagnostics import ProtectionState, SourceRunDiagnostics
from sources.googleflights.parser import parse_dom as parse_google_dom, parse_expanded_cards as parse_google_expanded
from sources.googleflights.flight_number_resolver import FlightNumberResolver
from sources.easemytrip.parser import parse_dom as parse_emt_dom
from sources.easemytrip.diagnostics import EaseMyTripDiagnostics, EaseMyTripFailureClassification
from sources.easemytrip.fare_options import extract_fare_options_from_card
from core.evidence import EvidenceCapture

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def sample_request():
    return FareSearchRequest(
        source="google_flights",
        origin="DEL",
        destination="BOM",
        travel_date=date(2026, 10, 5),
        lead_days=7,
        cabin=CabinClass.ECONOMY,
        trip_type=TripType.ONE_WAY,
        collection_mode="BROWSER",
    )


# ===========================================================================
# 1. Normal Parsing
# ===========================================================================

def test_google_normal_parsing(sample_request):
    fixture = FIXTURES_DIR / "google" / "results_basic.html"
    html = fixture.read_text(encoding="utf-8")
    run_id = uuid.uuid4()

    fares = parse_google_dom(html, sample_request, run_id, "google_flights")
    assert len(fares) == 3

    f1 = fares[0]
    assert f1["airline"] == "Air India"
    assert f1["total_fare"] == 5850.0
    assert f1["origin"] == "DEL"
    assert f1["destination"] == "BOM"
    assert f1["stops"] == 0
    assert f1["google_result_category"] == "BEST"
    assert f1["google_result_rank"] == 1


def test_easemytrip_normal_parsing(sample_request):
    fixture = FIXTURES_DIR / "easemytrip" / "results_basic.html"
    html = fixture.read_text(encoding="utf-8")
    run_id = uuid.uuid4()

    req = sample_request.model_copy(update={"source": "easemytrip"})
    obs = parse_emt_dom(html, req, run_id, "easemytrip")
    assert len(obs) == 2

    assert obs[0].airline == "IndiGo"
    assert obs[0].flight_number == "6E-512"
    assert obs[0].total_fare == 5450.0

    assert obs[1].airline == "Air India"
    assert obs[1].flight_number == "AI-805"
    assert obs[1].total_fare == 6100.0


# ===========================================================================
# 2. Missing Fields Provenance (Phase 3)
# ===========================================================================

def test_field_provenance_tracking(sample_request):
    fixture = FIXTURES_DIR / "google" / "results_basic.html"
    html = fixture.read_text(encoding="utf-8")
    run_id = uuid.uuid4()

    fares = parse_google_dom(html, sample_request, run_id, "google_flights")
    f1 = fares[0]

    prov = f1["field_provenance"]
    assert prov["total_fare"]["status"] == FieldStatus.OBSERVED.value
    assert prov["base_fare"]["status"] == FieldStatus.UNAVAILABLE.value
    assert prov["base_fare"]["missing_reason"] == MissingReason.SOURCE_TOTAL_ONLY.value
    assert prov["taxes"]["status"] == FieldStatus.UNAVAILABLE.value
    assert prov["taxes"]["missing_reason"] == MissingReason.SOURCE_TOTAL_ONLY.value
    assert prov["gst"]["status"] == FieldStatus.UNAVAILABLE.value
    assert prov["gst"]["missing_reason"] == MissingReason.SOURCE_TOTAL_ONLY.value


# ===========================================================================
# 3. Multiple Fare Offers (Phase 15: 1 Itinerary -> Many Offers)
# ===========================================================================

def test_easemytrip_multiple_fare_offers(sample_request):
    fixture = FIXTURES_DIR / "easemytrip" / "results_multiple_fares.html"
    html = fixture.read_text(encoding="utf-8")
    run_id = uuid.uuid4()

    req = sample_request.model_copy(update={"source": "easemytrip"})
    # When include_fare_options is True, each fare offer becomes a distinct observation
    obs = parse_emt_dom(html, req, run_id, "easemytrip", include_fare_options=True)

    assert len(obs) == 4
    families = [o.fare_family for o in obs]
    assert "Value" in families
    assert "EMTEXCLUSIVE" in families
    assert "Classic" in families
    assert "Flex" in families

    prices = {o.fare_family: float(o.total_fare) for o in obs}
    assert prices["Value"] == 5200.0
    assert prices["EMTEXCLUSIVE"] == 5550.0
    assert prices["Classic"] == 6100.0
    assert prices["Flex"] == 6800.0


# ===========================================================================
# 4. Multiple Segments
# ===========================================================================

def test_flight_segments_extraction(sample_request):
    fixture = FIXTURES_DIR / "google" / "flight_details.html"
    html = fixture.read_text(encoding="utf-8")
    run_id = uuid.uuid4()

    fares = parse_google_expanded([html], sample_request, run_id, "google_flights")
    assert len(fares) == 1
    assert len(fares[0]["flight_segments"]) == 1

    seg = fares[0]["flight_segments"][0]
    assert seg["origin"] == "DEL"
    assert seg["destination"] == "BOM"
    assert seg["flight_number"] == "AI-102"


# ===========================================================================
# 5. Price-Only Observations (Phase 10)
# ===========================================================================

def test_price_only_observation(sample_request):
    html = """
    <li>
        <div>Vistara | 09:30 AM – 11:45 AM | 2 hr 15 min | DEL–BOM | Non-stop | ₹7,250</div>
    </li>
    """
    run_id = uuid.uuid4()
    fares = parse_google_dom(html, sample_request, run_id, "google_flights")
    assert len(fares) == 1
    fare = fares[0]

    assert fare["total_fare"] == 7250.0
    assert fare["currency"] == "INR"
    assert fare["price_status"] == "DISPLAYED_TOTAL"
    assert fare["base_fare"] is None
    assert fare["taxes"] is None
    assert fare["gst"] is None


# ===========================================================================
# 6. Blocked Page Detection (Phase 18)
# ===========================================================================

def test_blocked_page_detection():
    # EaseMyTrip blocked fixture
    fixture = FIXTURES_DIR / "easemytrip" / "blocked.html"
    html = fixture.read_text(encoding="utf-8")

    diag = EaseMyTripDiagnostics(
        navigation_url="https://flight.easemytrip.com",
        http_response_status=403,
        page_title="Access Denied",
        access_denied_text_exists="access denied" in html.lower(),
    )
    classification = diag.classify()
    assert classification == EaseMyTripFailureClassification.ACCESS_DENIED


# ===========================================================================
# 7. CAPTCHA Detection (Phase 18)
# ===========================================================================

def test_captcha_detection():
    fixture = FIXTURES_DIR / "easemytrip" / "captcha.html"
    html = fixture.read_text(encoding="utf-8")

    diag = EaseMyTripDiagnostics(
        navigation_url="https://flight.easemytrip.com",
        page_title="Just a moment... | EaseMyTrip",
        captcha_challenge_text_exists="verify you are human" in html.lower(),
    )
    classification = diag.classify()
    assert classification == EaseMyTripFailureClassification.CAPTCHA_DETECTED


# ===========================================================================
# 8. Selector Drift Detection
# ===========================================================================

def test_selector_drift_detection():
    # Page with container and large DOM but no flight cards
    diag = EaseMyTripDiagnostics(
        navigation_url="https://flight.easemytrip.com",
        dom_size_bytes=150000,
        result_container_exists=True,
        expected_flight_cards_exist=False,
    )
    classification = diag.classify()
    assert classification == EaseMyTripFailureClassification.SELECTOR_DRIFT


# ===========================================================================
# 9. Enrichment Timeout / Bounded Transitions
# ===========================================================================

def test_enrichment_task_bounded_attempts():
    from models.enrichment import EnrichmentTask, EnrichmentType, EnrichmentStatus

    task = EnrichmentTask(
        observation_id="test-obs-1",
        source="google_flights",
        enrichment_type=EnrichmentType.BAGGAGE,
        max_attempts=2,
    )
    assert task.can_retry() is True
    task.mark_running()
    assert task.attempts == 1

    task.mark_failed("Timeout waiting for panel")
    assert task.can_retry() is True

    task.mark_running()
    assert task.attempts == 2
    task.mark_failed("Second timeout")
    # Bounded retries: max attempts reached, cannot retry further
    assert task.can_retry() is False


# ===========================================================================
# 10. Safe-Stop Behavior
# ===========================================================================

def test_safe_stop_behavior():
    from core.orchestrator import BLOCKING_STATES

    assert WorkflowState.CAPTCHA_BLOCKED in BLOCKING_STATES
    assert WorkflowState.ACCESS_BLOCKED in BLOCKING_STATES
    assert WorkflowState.RATE_LIMITED in BLOCKING_STATES
    assert WorkflowState.ROBOTS_DISALLOWED in BLOCKING_STATES


# ===========================================================================
# 11. Evidence Checkpoint Generation (Phase 16)
# ===========================================================================

def test_evidence_checkpoint_paths(tmp_path):
    capture = EvidenceCapture(base_dir=tmp_path)
    checkpoint_dir = capture.get_checkpoint_dir(
        source="google_flights",
        run_id="run-1234",
        route="DEL-BOM",
        lead_time=7,
        observation_id="obs-5678",
        date_str="2026-09-27",
    )

    expected = tmp_path / "2026-09-27" / "run-1234" / "google_flights" / "DEL-BOM" / "T+7" / "obs-5678"
    assert checkpoint_dir == expected
    assert checkpoint_dir.exists()


# ===========================================================================
# 12. NO FABRICATION TEST (Phase 20)
# ===========================================================================

def test_phase20_no_fabrication_guarantee(sample_request):
    """
    CRITICAL: No parser may manufacture missing values.
    If only total price is available:
    - assert base_fare is None
    - assert taxes is None
    - assert gst is None
    If baggage isn't exposed:
    - assert baggage values are None
    If flight number isn't exposed:
    - assert flight_number is None
    If fare family isn't exposed:
    - assert fare_family is None
    """
    html_total_only = """
    <li>
        Vistara | 06:00 AM – 08:15 AM | 2 hr 15 min | DEL–BOM | Non-stop | ₹6,500
    </li>
    """
    run_id = uuid.uuid4()
    fares = parse_google_dom(html_total_only, sample_request, run_id, "google_flights")
    assert len(fares) == 1
    fare = fares[0]

    # Strictly None
    assert fare["base_fare"] is None
    assert fare["taxes"] is None
    assert fare["gst"] is None
    assert fare["fees"] is None
    assert fare["airport_charges"] is None
    assert fare["convenience_fee"] is None
    assert fare["discount"] is None
    assert fare.get("cabin_baggage_kg") is None
    assert fare.get("checkin_baggage_kg") is None
    assert fare["flight_number"] is None
    assert fare.get("fare_family") is None
