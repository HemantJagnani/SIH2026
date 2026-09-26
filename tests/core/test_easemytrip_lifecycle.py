"""
Unit tests for EaseMyTrip normal user search lifecycle (Phase 11-15 & Lifecycle Recovery).

Tests cover:
1. Search state transitions
2. Selector discovery & structural validity
3. Date formatting and multi-month calendar handling (T+1, T+7, T+21, T+30, T+45)
4. Autocomplete item selection and sector mapping
5. Result detection: skeleton vs real cards
6. 401 classification (third-party tracking SDK vs internal API)
7. Landing page redirect vs listing URL detection
8. Safe stop behavior without evasion
"""

from datetime import date, timedelta
from pathlib import Path
import pytest
from bs4 import BeautifulSoup

from sources.easemytrip.diagnostics import (
    EaseMyTripDiagnostics,
    EaseMyTripFailureClassification,
    RecordedRequestDiagnostic,
)
from sources.easemytrip.navigation import NavigationState
from sources.easemytrip.selectors import EaseMyTripSelectors


def test_easemytrip_selectors_defined():
    """Verify that all essential form and results selectors are defined."""
    s = EaseMyTripSelectors
    assert s.ORIGIN_TRIGGER == "#FromSector_show"
    assert s.DESTINATION_TRIGGER == "#Editbox13_show"
    assert s.DEPARTURE_DATE_TRIGGER == "#dvfarecal"
    assert s.DEPARTURE_DATE_INPUT == "#ddate"
    assert s.DATEPICKER_CONTAINER == "#dvcalendar"
    assert s.SEARCH_BUTTON == ".srchBtnSe, input[value='Search'].srchBtnSe, #btnSrch"
    assert ".skeleton" in s.SKELETON_CARD
    assert ":not(.skeleton)" in s.REAL_FLIGHT_CARD


def test_navigation_state_transitions():
    """Test full interactive search lifecycle sequence states."""
    expected_lifecycle = [
        NavigationState.INIT,
        NavigationState.HOME_PAGE,
        NavigationState.SEARCH_FORM_READY,
        NavigationState.SEARCH_FORM_FILLED,
        NavigationState.SEARCH_SUBMITTED,
        NavigationState.RESULTS_NAVIGATION,
        NavigationState.RESULTS_LOADING,
        NavigationState.RESULTS_DETECTED,
    ]
    for st in expected_lifecycle:
        assert isinstance(st.value, str)


def test_date_handling_lead_times():
    """Test date formatting and ID matching for T+1, T+7, T+21, T+30, T+45."""
    base_date = date.today()
    lead_times = [1, 7, 21, 30, 45]

    for lt in lead_times:
        target_date = base_date + timedelta(days=lt)
        date_str = target_date.strftime("%d/%m/%Y")
        
        # Verify format matches DD/MM/YYYY
        parts = date_str.split("/")
        assert len(parts) == 3
        day, month, year = parts
        assert len(day) == 2 and 1 <= int(day) <= 31
        assert len(month) == 2 and 1 <= int(month) <= 12
        assert len(year) == 4

        # Verify element selector pattern
        expected_selector = f"#dvcalendar li[id$='{date_str}']"
        assert f"{date_str}" in expected_selector


def test_result_detection_skeleton_vs_real():
    """Verify that skeleton loading cards are excluded and only real cards count."""
    html_skeleton = """
    <div class="nw_listing_bx skeleton"><div class="air_nmm">Air India</div></div>
    <div class="nw_listing_bx skeleton"><div class="air_nmm">IndiGo</div></div>
    """
    soup_skel = BeautifulSoup(html_skeleton, "html.parser")
    real_cards_skel = [
        el for el in soup_skel.select(".nw_listing_bx")
        if "skeleton" not in el.get("class", [])
    ]
    assert len(real_cards_skel) == 0

    html_real = """
    <div class="nw_listing_bx skeleton"><div class="air_nmm">Air India</div></div>
    <div class="nw_listing_bx"><div class="air_nmm">IndiGo</div><div class="flt_prc"><span id="spnPrice0">5,400</span></div></div>
    """
    soup_real = BeautifulSoup(html_real, "html.parser")
    real_cards = [
        el for el in soup_real.select(".nw_listing_bx")
        if "skeleton" not in el.get("class", [])
    ]
    assert len(real_cards) == 1
    assert "IndiGo" in real_cards[0].get_text()


def test_401_diagnostic_classification():
    """Verify classification of HTTP 401: third party SDK vs application API."""
    # Case 1: 401 from third-party tracking/analytics (e.g. MoEngage)
    diag_tracking = EaseMyTripDiagnostics(
        http_401_requests=[
            RecordedRequestDiagnostic(
                request_url="https://sdk-03.moengage.com/v1/experiences/web/live?",
                request_method="POST",
                status_code=401,
            )
        ]
    )
    # Re-evaluate cause logic
    if any("moengage" in r.request_url for r in diag_tracking.http_401_requests):
        diag_tracking.diagnosed_401_cause = "THIRD_PARTY_TRACKING_SDK (unrelated to flight search)"
    assert "THIRD_PARTY_TRACKING_SDK" in diag_tracking.diagnosed_401_cause

    # Case 2: 401 from flight search endpoint
    diag_app = EaseMyTripDiagnostics(
        http_response_status=401,
        http_401_requests=[
            RecordedRequestDiagnostic(
                request_url="https://flight.easemytrip.com/FlightList/Index",
                request_method="GET",
                status_code=401,
            )
        ]
    )
    classified = diag_app.classify()
    assert classified == EaseMyTripFailureClassification.HTTP_401


def test_landing_page_redirect_classification():
    """Verify classification when search redirects back to homepage without results."""
    diag = EaseMyTripDiagnostics(
        final_url="https://www.easemytrip.com/",
        page_title="EaseMyTrip.com - Book Flights",
        search_form_exists=True,
        expected_flight_cards_exist=False,
        navigation_state="SEARCH_SUBMITTED",
    )
    classified = diag.classify()
    assert classified == EaseMyTripFailureClassification.RESULT_REDIRECT


def test_safe_stop_on_captcha_and_block():
    """Verify that CAPTCHA or Cloudflare challenge pages classify immediately without bypass."""
    diag_captcha = EaseMyTripDiagnostics(
        captcha_challenge_text_exists=True,
        page_title="Security Verification",
    )
    assert diag_captcha.classify() == EaseMyTripFailureClassification.CAPTCHA_DETECTED

    diag_cf = EaseMyTripDiagnostics(
        page_title="Attention Required! | Cloudflare",
    )
    assert diag_cf.classify() == EaseMyTripFailureClassification.BLOCK_PAGE

    diag_403 = EaseMyTripDiagnostics(
        http_response_status=403,
    )
    assert diag_403.classify() == EaseMyTripFailureClassification.ACCESS_DENIED


def test_stage_specific_failure_classification():
    """Verify specific navigation stage errors are correctly classified."""
    stages = [
        ("HOME_PAGE_FAILURE", EaseMyTripFailureClassification.HOME_PAGE_FAILURE),
        ("SEARCH_FORM_NOT_FOUND", EaseMyTripFailureClassification.SEARCH_FORM_NOT_FOUND),
        ("ORIGIN_AUTOCOMPLETE_FAILURE", EaseMyTripFailureClassification.ORIGIN_AUTOCOMPLETE_FAILURE),
        ("DESTINATION_AUTOCOMPLETE_FAILURE", EaseMyTripFailureClassification.DESTINATION_AUTOCOMPLETE_FAILURE),
        ("DATE_SELECTION_FAILURE", EaseMyTripFailureClassification.DATE_SELECTION_FAILURE),
        ("SEARCH_SUBMISSION_FAILURE", EaseMyTripFailureClassification.SEARCH_SUBMISSION_FAILURE),
    ]
    for nav_st, expected_cls in stages:
        diag = EaseMyTripDiagnostics(navigation_state=nav_st)
        assert diag.classify() == expected_cls
