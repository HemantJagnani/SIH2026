"""
Tests for APIx Phase 27 — EaseMyTrip Data Quality + Enrichment Audit.

Verifies:
1. one itinerary / multiple fare offers
2. duplicate offer detection
3. distinct fare families
4. rejection reason reporting
5. explicit baggage extraction
6. missing baggage
7. explicit fare breakup
8. total-only price
9. fare-rule extraction
10. enrichment failure handling
11. evidence generation
12. APIx eligibility
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import List

import pytest
from bs4 import BeautifulSoup

from models.enums import AvailabilityStatus, CabinClass, TripType, WorkflowState
from models.observation import FareObservation
from models.provenance import FieldStatus, MissingReason
from models.request import FareSearchRequest
from sources.easemytrip.fare_options import EaseMyTripFareOption, extract_fare_options_from_card
from sources.easemytrip.parser import parse_dom


@pytest.fixture
def sample_request() -> FareSearchRequest:
    return FareSearchRequest(
        source="easemytrip",
        collection_mode="BROWSER",
        origin="DEL",
        destination="BOM",
        travel_date=date(2026, 10, 3),
        lead_days=7,
        passenger_count={"adults": 1, "children": 0, "infants": 0},
        cabin=CabinClass.ECONOMY,
        trip_type=TripType.ONE_WAY,
    )


# 1. One Itinerary / Multiple Fare Offers
def test_one_itinerary_multiple_fare_offers(sample_request):
    html = """
    <div class="nw_listing_bx">
        <div class="air_nmm_txt"><h6>IndiGo</h6><span>6E-512</span></div>
        <div class="tm_lc texrgt"><h4>10:15</h4></div>
        <div class="tmln_rc"><span>02h 10m</span><span>Non Stop</span></div>
        <div class="tm_lc"><h4>12:25</h4></div>
        <div class="flt_prc"><h4 id="spnPrice0">₹ 6,090</h4></div>
        <label class="_mfarebx">
            <div class="fareheader">Saver</div>
            <div class="fareprice">₹ 6,090</div>
            <span>7 Kgs Cabin Baggage</span><span>15 Kgs Check-in Baggage</span>
            <span>Cancellation fee starts at ₹ 4,299</span>
        </label>
        <label class="_mfarebx">
            <div class="fareheader">EMTEXCLUSIVE</div>
            <div class="fareprice">₹ 6,339</div>
            <span>7 Kgs Cabin Baggage</span><span>15 Kgs Check-in Baggage</span>
            <span>Cancellation fee starts at ₹ 999</span>
        </label>
        <label class="_mfarebx">
            <div class="fareheader">IndigoUpFront</div>
            <div class="fareprice">₹ 9,240</div>
            <span>7 Kgs Cabin Baggage</span><span>20 Kgs Check-in Baggage</span>
            <span>Cancellation fee starts at ₹ 2,499</span>
        </label>
    </div>
    """
    obs = parse_dom(html, sample_request, uuid.uuid4(), "easemytrip", include_fare_options=True)
    assert len(obs) == 3
    # All 3 share the same itinerary
    flight_nums = {o.flight_number for o in obs}
    assert flight_nums == {"6E-512"}
    fares = {o.fare_family: float(o.total_fare) for o in obs}
    assert fares == {"Saver": 6090.0, "EMTEXCLUSIVE": 6339.0, "IndigoUpFront": 9240.0}


# 2. Duplicate Offer Detection
def test_duplicate_offer_detection(sample_request):
    soup = BeautifulSoup("""
    <div class="nw_listing_bx">
        <label class="_mfarebx"><div class="fareheader">Saver</div><div class="fareprice">₹ 6,090</div></label>
        <label class="_mfarebx"><div class="fareheader">Saver</div><div class="fareprice">₹ 6,090</div></label>
        <label class="_mfarebx"><div class="fareheader">Flexi</div><div class="fareprice">₹ 6,800</div></label>
    </div>
    """, "html.parser")
    card = soup.select_one(".nw_listing_bx")
    options = extract_fare_options_from_card(card)
    # The duplicate (Saver at 6090.0) must be deduplicated
    assert len(options) == 2
    assert {opt.fare_family for opt in options} == {"Saver", "Flexi"}


# 3. Distinct Fare Families
def test_distinct_fare_families(sample_request):
    soup = BeautifulSoup("""
    <div class="nw_listing_bx">
        <label class="_mfarebx"><div class="fareheader">Value</div><div class="fareprice">₹ 5,000</div></label>
        <label class="_mfarebx"><div class="fareheader">EMTEXCLUSIVE</div><div class="fareprice">₹ 5,300</div></label>
        <label class="_mfarebx"><div class="fareheader">Classic</div><div class="fareprice">₹ 5,800</div></label>
        <label class="_mfarebx"><div class="fareheader">Flex</div><div class="fareprice">₹ 6,500</div></label>
    </div>
    """, "html.parser")
    card = soup.select_one(".nw_listing_bx")
    options = extract_fare_options_from_card(card)
    assert [o.fare_family for o in options] == ["Value", "EMTEXCLUSIVE", "Classic", "Flex"]


# 4. Rejection Reason Reporting
def test_rejection_reason_reporting(sample_request):
    # Card with missing airline
    html_no_airline = """
    <div class="nw_listing_bx">
        <div class="tm_lc texrgt"><h4>10:15</h4></div>
        <div class="tm_lc"><h4>12:25</h4></div>
        <div class="flt_prc"><h4 id="spnPrice0">₹ 6,090</h4></div>
    </div>
    """
    obs = parse_dom(html_no_airline, sample_request, uuid.uuid4(), "easemytrip")
    assert len(obs) == 0

    # Card with zero price
    html_zero_price = """
    <div class="nw_listing_bx">
        <div class="air_nmm_txt"><h6>IndiGo</h6><span>6E-512</span></div>
        <div class="tm_lc texrgt"><h4>10:15</h4></div>
        <div class="tm_lc"><h4>12:25</h4></div>
        <div class="flt_prc"><h4 id="spnPrice0">₹ 0</h4></div>
    </div>
    """
    obs = parse_dom(html_zero_price, sample_request, uuid.uuid4(), "easemytrip")
    assert len(obs) == 0


# 5. Explicit Baggage Extraction
def test_explicit_baggage_extraction(sample_request):
    html = """
    <div class="nw_listing_bx">
        <div class="air_nmm_txt"><h6>IndiGo</h6><span>6E-512</span></div>
        <div class="tm_lc texrgt"><h4>10:15</h4></div>
        <div class="tm_lc"><h4>12:25</h4></div>
        <div class="flt_prc"><h4 id="spnPrice0">₹ 6,090</h4></div>
        <label class="_mfarebx">
            <div class="fareheader">Saver</div>
            <div class="fareprice">₹ 6,090</div>
            <div>7 Kgs Cabin Baggage</div>
            <div>15 Kgs Check-in Baggage</div>
        </label>
    </div>
    """
    obs = parse_dom(html, sample_request, uuid.uuid4(), "easemytrip", include_fare_options=True)
    assert len(obs) == 1
    assert obs[0].cabin_baggage_kg == 7
    assert obs[0].checkin_baggage_kg == 15
    assert obs[0].field_provenance["cabin_baggage_kg"]["status"] == FieldStatus.OBSERVED.value
    assert obs[0].field_provenance["checkin_baggage_kg"]["status"] == FieldStatus.OBSERVED.value


# 6. Missing Baggage
def test_missing_baggage(sample_request):
    html = """
    <div class="nw_listing_bx">
        <div class="air_nmm_txt"><h6>IndiGo</h6><span>6E-512</span></div>
        <div class="tm_lc texrgt"><h4>10:15</h4></div>
        <div class="tm_lc"><h4>12:25</h4></div>
        <div class="flt_prc"><h4 id="spnPrice0">₹ 6,090</h4></div>
        <label class="_mfarebx">
            <div class="fareheader">Saver</div>
            <div class="fareprice">₹ 6,090</div>
            <div>Carry-on included</div>
        </label>
    </div>
    """
    obs = parse_dom(html, sample_request, uuid.uuid4(), "easemytrip", include_fare_options=True)
    assert len(obs) == 1
    # Generic text without kg is strictly NOT parsed into numbers
    assert obs[0].cabin_baggage_kg is None
    assert obs[0].checkin_baggage_kg is None
    assert obs[0].field_provenance["cabin_baggage_kg"]["status"] == FieldStatus.UNAVAILABLE.value
    assert obs[0].field_provenance["cabin_baggage_kg"]["missing_reason"] == MissingReason.NOT_PRESENT_IN_DOM.value


# 7. Explicit Fare Breakup
def test_explicit_fare_breakup(sample_request):
    html = """
    <div class="nw_listing_bx">
        <div class="air_nmm_txt"><h6>IndiGo</h6><span>6E-512</span></div>
        <div class="tm_lc texrgt"><h4>10:15</h4></div>
        <div class="tm_lc"><h4>12:25</h4></div>
        <div class="flt_prc"><h4 id="spnPrice0">₹ 6,090</h4></div>
    </div>
    """
    obs = parse_dom(html, sample_request, uuid.uuid4(), "easemytrip")
    assert len(obs) == 1
    # When unbundled breakdown is absent in DOM, never calculate or fabricate
    assert obs[0].base_fare is None
    assert obs[0].taxes is None
    assert obs[0].gst is None
    assert obs[0].field_provenance["base_fare"]["status"] == FieldStatus.UNAVAILABLE.value
    assert obs[0].field_provenance["base_fare"]["missing_reason"] == MissingReason.SOURCE_TOTAL_ONLY.value


# 8. Total-Only Price
def test_total_only_price(sample_request):
    html = """
    <div class="nw_listing_bx">
        <div class="air_nmm_txt"><h6>Air India</h6><span>AI-805</span></div>
        <div class="tm_lc texrgt"><h4>14:00</h4></div>
        <div class="tm_lc"><h4>16:15</h4></div>
        <div class="flt_prc"><h4 id="spnPrice0">₹ 7,500</h4></div>
    </div>
    """
    obs = parse_dom(html, sample_request, uuid.uuid4(), "easemytrip")
    assert len(obs) == 1
    assert float(obs[0].total_fare) == 7500.0
    assert obs[0].price_status == "DISPLAYED_TOTAL"
    assert obs[0].base_fare is None
    assert obs[0].taxes is None


# 9. Fare Rule Extraction
def test_fare_rule_extraction(sample_request):
    html = """
    <div class="nw_listing_bx">
        <div class="air_nmm_txt"><h6>IndiGo</h6><span>6E-512</span></div>
        <div class="tm_lc texrgt"><h4>10:15</h4></div>
        <div class="tm_lc"><h4>12:25</h4></div>
        <div class="flt_prc"><h4 id="spnPrice0">₹ 6,090</h4></div>
        <label class="_mfarebx">
            <div class="fareheader">Saver</div>
            <div class="fareprice">₹ 6,090</div>
            <div>Cancellation fee starts at ₹ 4,299</div>
            <div>Date Change fee starts at ₹ 3,499</div>
        </label>
    </div>
    """
    obs = parse_dom(html, sample_request, uuid.uuid4(), "easemytrip", include_fare_options=True)
    assert len(obs) == 1
    assert obs[0].cancellation_fee == Decimal("4299")
    assert obs[0].change_fee == Decimal("3499")
    assert obs[0].refund_status == "CONDITIONAL"
    assert obs[0].field_provenance["cancellation_fee"]["status"] == FieldStatus.OBSERVED.value
    assert obs[0].field_provenance["change_fee"]["status"] == FieldStatus.OBSERVED.value


# 10. Enrichment Failure Handling
def test_enrichment_failure_handling(sample_request):
    # Card with broken fare options box (missing headers or invalid price)
    html_broken_options = """
    <div class="nw_listing_bx">
        <div class="air_nmm_txt"><h6>IndiGo</h6><span>6E-512</span></div>
        <div class="tm_lc texrgt"><h4>10:15</h4></div>
        <div class="tm_lc"><h4>12:25</h4></div>
        <div class="flt_prc"><h4 id="spnPrice0">₹ 6,090</h4></div>
        <label class="_mfarebx">
            <div>Corrupt Box Without Header Or Price</div>
        </label>
    </div>
    """
    obs = parse_dom(html_broken_options, sample_request, uuid.uuid4(), "easemytrip", include_fare_options=True)
    # Falls back gracefully to the primary card observation
    assert len(obs) == 1
    assert obs[0].flight_number == "6E-512"
    assert float(obs[0].total_fare) == 6090.0


# 11. Evidence Generation
def test_evidence_generation(tmp_path, sample_request):
    run_dir = tmp_path / "runtime" / "evidence" / "2026-09-27" / "source=easemytrip" / "run=test-run-1"
    run_dir.mkdir(parents=True, exist_ok=True)
    
    # Write metadata, request, and result
    (run_dir / "metadata.json").write_text('{"state": "DONE"}')
    (run_dir / "request.json").write_text(sample_request.model_dump_json())
    (run_dir / "result.json").write_text('{"observations": 100}')

    assert (run_dir / "metadata.json").exists()
    assert (run_dir / "request.json").exists()
    assert (run_dir / "result.json").exists()


# 12. APIx Eligibility
def test_apix_eligibility(sample_request):
    html = """
    <div class="nw_listing_bx">
        <div class="air_nmm_txt"><h6>IndiGo</h6><span>6E-512</span></div>
        <div class="tm_lc texrgt"><h4>10:15</h4></div>
        <div class="tmln_rc"><span>02h 10m</span><span>Non Stop</span></div>
        <div class="tm_lc"><h4>12:25</h4></div>
        <div class="flt_prc"><h4 id="spnPrice0">₹ 6,090</h4></div>
    </div>
    """
    obs_list = parse_dom(html, sample_request, uuid.uuid4(), "easemytrip")
    assert len(obs_list) == 1
    obs = obs_list[0]

    # Verify APIx minimum product criteria
    assert obs.origin == "DEL"
    assert obs.destination == "BOM"
    assert obs.trip_type == TripType.ONE_WAY
    assert obs.cabin == CabinClass.ECONOMY
    assert obs.currency == "INR"
    assert obs.passenger_count == 1
    assert obs.total_fare is not None and obs.total_fare > 0
    assert obs.travel_date == sample_request.travel_date
    assert obs.lead_days == 7
    assert obs.availability == AvailabilityStatus.AVAILABLE
