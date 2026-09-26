"""
EaseMyTrip Diagnostics and Failure Classifier (Extended for Normal Search Lifecycle).

Captures diagnostic evidence to determine why EaseMyTrip fails or gets blocked
without guessing or attempting anti-bot circumvention.
"""

from __future__ import annotations

import hashlib
import json
import logging
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class EaseMyTripFailureClassification(str, Enum):
    # Navigation & Form Lifecycle
    HOME_PAGE_FAILURE = "HOME_PAGE_FAILURE"
    SEARCH_FORM_NOT_FOUND = "SEARCH_FORM_NOT_FOUND"
    ORIGIN_AUTOCOMPLETE_FAILURE = "ORIGIN_AUTOCOMPLETE_FAILURE"
    DESTINATION_AUTOCOMPLETE_FAILURE = "DESTINATION_AUTOCOMPLETE_FAILURE"
    DATE_SELECTION_FAILURE = "DATE_SELECTION_FAILURE"
    SEARCH_SUBMISSION_FAILURE = "SEARCH_SUBMISSION_FAILURE"
    RESULT_REDIRECT = "RESULT_REDIRECT"
    RESULTS_TIMEOUT = "RESULTS_TIMEOUT"
    NO_RESULTS = "NO_RESULTS"
    PAGE_NOT_REACHED = "PAGE_NOT_REACHED"
    SEARCH_NOT_SUBMITTED = "SEARCH_NOT_SUBMITTED"

    # HTTP & Protection States
    HTTP_401 = "HTTP_401"
    HTTP_403 = "HTTP_403"
    HTTP_429 = "HTTP_429"
    BLOCK_PAGE = "BLOCK_PAGE"
    CAPTCHA_DETECTED = "CAPTCHA_DETECTED"
    PROTECTION_DETECTED = "PROTECTION_DETECTED"
    ACCESS_DENIED = "ACCESS_DENIED"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    SERVER_ERROR = "SERVER_ERROR"

    # Parsing & Selector States
    PARSER_FAILURE = "PARSER_FAILURE"
    SELECTOR_DRIFT = "SELECTOR_DRIFT"
    UNKNOWN = "UNKNOWN"


class RecordedRequestDiagnostic(BaseModel):
    """Sanitized network request diagnostic entry (no secrets, cookies, or auth tokens)."""
    request_url: str
    request_method: str
    status_code: int
    resource_type: Optional[str] = None
    initiator: Optional[str] = None
    timestamp: Optional[str] = None


class EaseMyTripDiagnostics(BaseModel):
    """
    Detailed diagnostic capture for EaseMyTrip session.
    """
    navigation_url: Optional[str] = None
    http_response_status: Optional[int] = None
    final_url: Optional[str] = None
    page_title: Optional[str] = None
    body_text_fingerprint: Optional[str] = None
    dom_size_bytes: int = 0
    expected_flight_cards_exist: bool = False
    search_form_exists: bool = False
    result_container_exists: bool = False
    captcha_challenge_text_exists: bool = False
    access_denied_text_exists: bool = False
    login_session_state_changed: bool = False
    browser_console_errors: List[str] = Field(default_factory=list)
    failed_requests_count: int = 0
    request_response_status_summary: Dict[str, int] = Field(default_factory=dict)
    http_401_requests: List[RecordedRequestDiagnostic] = Field(default_factory=list)
    diagnosed_401_cause: Optional[str] = None
    timeout_stage: Optional[str] = None
    navigation_state: Optional[str] = None
    failure_classification: EaseMyTripFailureClassification = EaseMyTripFailureClassification.UNKNOWN

    def classify(self) -> EaseMyTripFailureClassification:
        """
        Classifies the exact failure cause based on captured diagnostics.
        """
        # Specific stage failures set by navigation state machine
        if self.navigation_state:
            stage_map = {
                "HOME_PAGE_FAILURE": EaseMyTripFailureClassification.HOME_PAGE_FAILURE,
                "SEARCH_FORM_NOT_FOUND": EaseMyTripFailureClassification.SEARCH_FORM_NOT_FOUND,
                "ORIGIN_AUTOCOMPLETE_FAILURE": EaseMyTripFailureClassification.ORIGIN_AUTOCOMPLETE_FAILURE,
                "DESTINATION_AUTOCOMPLETE_FAILURE": EaseMyTripFailureClassification.DESTINATION_AUTOCOMPLETE_FAILURE,
                "DATE_SELECTION_FAILURE": EaseMyTripFailureClassification.DATE_SELECTION_FAILURE,
                "SEARCH_SUBMISSION_FAILURE": EaseMyTripFailureClassification.SEARCH_SUBMISSION_FAILURE,
                "RESULT_REDIRECT": EaseMyTripFailureClassification.RESULT_REDIRECT,
            }
            if self.navigation_state in stage_map:
                self.failure_classification = stage_map[self.navigation_state]
                return self.failure_classification

        if self.captcha_challenge_text_exists:
            self.failure_classification = EaseMyTripFailureClassification.CAPTCHA_DETECTED
            return self.failure_classification

        if self.access_denied_text_exists or (self.http_response_status and self.http_response_status in (403, 451)):
            self.failure_classification = EaseMyTripFailureClassification.ACCESS_DENIED
            return self.failure_classification

        if self.http_response_status:
            if self.http_response_status == 401:
                self.failure_classification = EaseMyTripFailureClassification.HTTP_401
                return self.failure_classification
            elif self.http_response_status == 429:
                self.failure_classification = EaseMyTripFailureClassification.HTTP_429
                return self.failure_classification
            elif 500 <= self.http_response_status < 600:
                self.failure_classification = EaseMyTripFailureClassification.SERVER_ERROR
                return self.failure_classification

        title_lower = (self.page_title or "").lower()
        if "just a moment" in title_lower or "attention required" in title_lower or "cloudflare" in title_lower:
            self.failure_classification = EaseMyTripFailureClassification.BLOCK_PAGE
            return self.failure_classification

        if self.final_url and "flight-search/listing" not in self.final_url and "FlightList" not in self.final_url:
            if self.navigation_state == "SEARCH_SUBMITTED":
                self.failure_classification = EaseMyTripFailureClassification.RESULT_REDIRECT
                return self.failure_classification

        if self.result_container_exists and not self.expected_flight_cards_exist:
            if self.dom_size_bytes > 50000:
                self.failure_classification = EaseMyTripFailureClassification.SELECTOR_DRIFT
            else:
                self.failure_classification = EaseMyTripFailureClassification.NO_RESULTS
            return self.failure_classification

        if self.timeout_stage:
            self.failure_classification = EaseMyTripFailureClassification.RESULTS_TIMEOUT
            return self.failure_classification

        if not self.final_url or self.final_url == "about:blank":
            self.failure_classification = EaseMyTripFailureClassification.PAGE_NOT_REACHED
            return self.failure_classification

        return self.failure_classification

    @classmethod
    async def capture_from_page(
        cls,
        page: Any,
        navigation_url: str,
        console_errors: List[str],
        request_summary: Dict[str, int],
        timeout_stage: Optional[str] = None,
        navigation_state: Optional[str] = None,
        http_status: Optional[int] = None,
        http_401_records: Optional[List[RecordedRequestDiagnostic]] = None,
    ) -> "EaseMyTripDiagnostics":
        """
        Inspect the live page to extract comprehensive diagnostics.
        """
        diag = cls(
            navigation_url=navigation_url,
            http_response_status=http_status,
            browser_console_errors=list(console_errors),
            request_response_status_summary=dict(request_summary),
            http_401_requests=list(http_401_records or []),
            timeout_stage=timeout_stage,
            navigation_state=navigation_state,
        )

        # Diagnose 401 cause if 401s occurred
        if diag.http_401_requests:
            urls = [r.request_url for r in diag.http_401_requests]
            if any("moengage" in u or "analytics" in u or "clarity" in u for u in urls):
                diag.diagnosed_401_cause = "THIRD_PARTY_TRACKING_SDK (unrelated to flight search)"
            elif any("FlightList" in u or "flight-search" in u for u in urls):
                diag.diagnosed_401_cause = "APPLICATION_API_REJECTION (flight search endpoint 401)"
            else:
                diag.diagnosed_401_cause = "OTHER_APPLICATION_ERROR"

        try:
            diag.final_url = page.url
        except Exception:
            pass

        try:
            diag.page_title = await page.title()
        except Exception:
            pass

        try:
            content = await page.content()
            diag.dom_size_bytes = len(content.encode("utf-8"))
            body_text = (await page.locator("body").inner_text()).lower()
            diag.body_text_fingerprint = hashlib.sha256(body_text[:1000].encode("utf-8")).hexdigest()[:16]

            # Check protection markers
            captcha_markers = [
                "captcha", "verify you are human", "checking your browser",
                "challenge", "turnstile", "cf-challenge", "human verification"
            ]
            diag.captcha_challenge_text_exists = any(m in body_text for m in captcha_markers)

            access_markers = [
                "access denied", "403 forbidden", "unauthorized request",
                "security violation", "blocked by cloudflare", "rate limit exceeded"
            ]
            diag.access_denied_text_exists = any(m in body_text for m in access_markers)

            # Check DOM structures
            diag.expected_flight_cards_exist = (
                await page.locator(".nw_listing_bx:not(.skeleton), .flt-list-item:not(.skeleton)").count()
            ) > 0
            diag.search_form_exists = (
                await page.locator("#frmHome, form#FrmEmtMdl, #FromSector_show").count()
            ) > 0
            diag.result_container_exists = (
                await page.locator(".flt-res-card, .row.top-srh, #flt-lst, .listing_left, .nw_listing_bx").count()
            ) > 0

        except Exception as exc:
            logger.warning(f"EaseMyTripDiagnostics: Error reading page DOM: {exc}")

        diag.classify()
        return diag
