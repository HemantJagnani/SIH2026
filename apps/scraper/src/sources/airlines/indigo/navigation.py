"""
navigation.py — IndiGo-specific browser workflow (state machine).

Implements the Phase 9 state machine sequence for the IndiGo search form:

  CREATED → POLICY_CHECK → OPEN_SOURCE → WAIT_PAGE_READY
  → HANDLE_CONSENT → ENTER_ORIGIN → ENTER_DESTINATION
  → SELECT_DATE → SELECT_PASSENGERS → SUBMIT_SEARCH
  → WAIT_RESULT_STATE → (EXTRACT / failure state)

Each function corresponds to one state transition. The CollectionOrchestrator
calls `run_search_workflow()` which executes these in order, short-circuiting
on any failure state.

Compliance rules enforced here:
  - Condition-based waits only (no arbitrary sleep() calls in the main flow)
  - No selector that defeats a protection mechanism
  - Any detection of CAPTCHA / 403 / login wall must immediately return the
    corresponding WorkflowState (caller captures evidence and stops)
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date
from typing import Optional

from models.enums import WorkflowState
from models.request import FareSearchRequest
from core.anti_bot_detector import captcha_present, is_login_wall

from . import selectors

logger = logging.getLogger(__name__)

# IndiGo home page.
INDIGO_URL = "https://www.goindigo.in/"

# Max time to wait for results container to appear (ms).
RESULTS_WAIT_TIMEOUT_MS = 45_000

# Short pause after critical interactions to let JS re-render settle.
# Using a small fixed wait here is acceptable per spec — it is not a
# "defeat mechanism", it is accommodating normal JS rendering latency.
_JS_SETTLE_MS = 500


async def open_source(page) -> WorkflowState:
    """
    Navigate to the IndiGo home page and wait for the booking widget to appear.
    State: OPEN_SOURCE → WAIT_PAGE_READY
    """
    logger.info("IndiGo navigation: opening %s", INDIGO_URL)
    try:
        await page.goto(INDIGO_URL, wait_until="domcontentloaded")
    except Exception as exc:
        logger.error("IndiGo navigation: failed to load page — %s", exc)
        return WorkflowState.SEARCH_ERROR

    return WorkflowState.WAIT_PAGE_READY


async def wait_page_ready(page) -> WorkflowState:
    """
    Confirm the booking widget is present and the page is interactive.
    State: WAIT_PAGE_READY → HANDLE_CONSENT
    """
    try:
        await page.wait_for_selector(selectors.BOOKING_WIDGET, timeout=20_000)
        logger.info("IndiGo navigation: booking widget ready.")
    except Exception:
        # Widget didn't appear — could be a block, slow load, or schema change.
        # Check for CAPTCHA before classifying as schema change.
        if await captcha_present(page):
            return WorkflowState.CAPTCHA_BLOCKED
        if await is_login_wall(page):
            return WorkflowState.AUTH_REQUIRED
        logger.warning("IndiGo navigation: booking widget not found — possible schema change.")
        return WorkflowState.SCHEMA_CHANGED

    return WorkflowState.HANDLE_CONSENT


async def handle_consent(page) -> WorkflowState:
    """
    Dismiss a cookie/consent banner if one appears. Non-fatal if absent.
    State: HANDLE_CONSENT → ENTER_ORIGIN
    """
    try:
        # Consent banners may take a moment to appear after page load.
        accept_btn = page.locator(selectors.CONSENT_ACCEPT).first
        if await accept_btn.is_visible(timeout=3_000):
            await accept_btn.click()
            logger.info("IndiGo navigation: consent banner accepted.")
            await page.wait_for_timeout(_JS_SETTLE_MS)
    except Exception:
        # No consent banner is fine — continue.
        pass

    return WorkflowState.ENTER_ORIGIN


async def select_one_way(page) -> None:
    """
    Ensure the One-Way tab is selected before filling the form.
    IndiGo sometimes defaults to Round-Trip.
    """
    try:
        one_way = page.locator(selectors.ONE_WAY_TAB).first
        if await one_way.is_visible(timeout=3_000):
            await one_way.click()
            await page.wait_for_timeout(_JS_SETTLE_MS)
            logger.info("IndiGo navigation: One-Way selected.")
    except Exception:
        pass  # Tab not found or already selected — continue.


async def enter_origin(page, origin: str) -> WorkflowState:
    """
    Fill the origin airport field and select from the autocomplete dropdown.
    State: ENTER_ORIGIN → ENTER_DESTINATION
    """
    logger.info("IndiGo navigation: entering origin '%s'.", origin)
    try:
        origin_field = page.locator(selectors.ORIGIN_INPUT).first
        await origin_field.click()
        await origin_field.fill(origin)
        # Wait for autocomplete suggestions to appear.
        await page.wait_for_selector(selectors.AUTOCOMPLETE_DROPDOWN, timeout=8_000)
        # Select the first suggestion (which matches the IATA code we typed).
        first_option = page.locator(selectors.AUTOCOMPLETE_FIRST_OPTION).first
        await first_option.click()
        await page.wait_for_timeout(_JS_SETTLE_MS)
    except Exception as exc:
        if await captcha_present(page):
            return WorkflowState.CAPTCHA_BLOCKED
        logger.error("IndiGo navigation: failed to enter origin — %s", exc)
        return WorkflowState.SEARCH_ERROR

    return WorkflowState.ENTER_DESTINATION


async def enter_destination(page, destination: str) -> WorkflowState:
    """
    Fill the destination airport field and select from the autocomplete dropdown.
    State: ENTER_DESTINATION → SELECT_DATE
    """
    logger.info("IndiGo navigation: entering destination '%s'.", destination)
    try:
        dest_field = page.locator(selectors.DESTINATION_INPUT).first
        await dest_field.click()
        await dest_field.fill(destination)
        await page.wait_for_selector(selectors.AUTOCOMPLETE_DROPDOWN, timeout=8_000)
        first_option = page.locator(selectors.AUTOCOMPLETE_FIRST_OPTION).first
        await first_option.click()
        await page.wait_for_timeout(_JS_SETTLE_MS)
    except Exception as exc:
        if await captcha_present(page):
            return WorkflowState.CAPTCHA_BLOCKED
        logger.error("IndiGo navigation: failed to enter destination — %s", exc)
        return WorkflowState.SEARCH_ERROR

    return WorkflowState.SELECT_DATE


async def select_date(page, travel_date: date) -> WorkflowState:
    """
    Open the date picker and select the travel date.
    State: SELECT_DATE → SELECT_PASSENGERS
    """
    logger.info("IndiGo navigation: selecting date %s.", travel_date)
    try:
        date_btn = page.locator(selectors.DEPARTURE_DATE_INPUT).first
        await date_btn.click()
        await page.wait_for_timeout(_JS_SETTLE_MS)

        # Try clicking the specific date cell. Playwright aria-label format
        # varies by site; we try the data-date attribute first, then text.
        date_str = travel_date.strftime("%Y-%m-%d")
        date_label = travel_date.strftime("%-d %B %Y")  # e.g. "5 October 2026"

        # Build selector with actual date values substituted.
        date_selector = (
            f'[data-date="{date_str}"], '
            f'button[aria-label*="{date_label}"], '
            f'td[aria-label*="{date_label}"]'
        )
        await page.wait_for_selector(date_selector, timeout=8_000)
        await page.locator(date_selector).first.click()
        await page.wait_for_timeout(_JS_SETTLE_MS)
    except Exception as exc:
        logger.error("IndiGo navigation: failed to select date — %s", exc)
        return WorkflowState.SEARCH_ERROR

    return WorkflowState.SELECT_PASSENGERS


async def select_passengers(page, adults: int = 1) -> WorkflowState:
    """
    Set passenger count. For the M4 POC we only support 1 adult.
    State: SELECT_PASSENGERS → SUBMIT_SEARCH
    """
    # For 1 adult (default), the form usually initialises to 1 — nothing to do.
    if adults == 1:
        logger.info("IndiGo navigation: 1 adult (default) — no change needed.")
        return WorkflowState.SUBMIT_SEARCH

    # For >1 adult, open the passenger panel and increment.
    try:
        pax_btn = page.locator(selectors.PASSENGER_SELECTOR).first
        await pax_btn.click()
        increase_btn = page.locator(selectors.ADULT_INCREASE_BTN).first
        for _ in range(adults - 1):
            await increase_btn.click()
            await page.wait_for_timeout(200)
    except Exception as exc:
        logger.error("IndiGo navigation: failed to set passengers — %s", exc)
        return WorkflowState.SEARCH_ERROR

    return WorkflowState.SUBMIT_SEARCH


async def submit_search(page) -> WorkflowState:
    """
    Click the Search button and wait for navigation to the results page.
    State: SUBMIT_SEARCH → WAIT_RESULT_STATE
    """
    logger.info("IndiGo navigation: submitting search.")
    try:
        search_btn = page.locator(selectors.SEARCH_BUTTON).first
        await search_btn.click()
    except Exception as exc:
        if await captcha_present(page):
            return WorkflowState.CAPTCHA_BLOCKED
        logger.error("IndiGo navigation: search button click failed — %s", exc)
        return WorkflowState.SEARCH_ERROR

    return WorkflowState.WAIT_RESULT_STATE


async def wait_result_state(page) -> WorkflowState:
    """
    After search submission, wait for a definitive result state:
      - Results container appeared → EXTRACT
      - CAPTCHA detected → CAPTCHA_BLOCKED
      - Login wall → AUTH_REQUIRED
      - No results text → NO_RESULTS
      - Timeout → SEARCH_ERROR
    State: WAIT_RESULT_STATE → EXTRACT | CAPTCHA_BLOCKED | AUTH_REQUIRED | NO_RESULTS | SEARCH_ERROR
    """
    logger.info("IndiGo navigation: waiting for result state (timeout %dms).", RESULTS_WAIT_TIMEOUT_MS)
    try:
        await page.wait_for_selector(selectors.RESULTS_CONTAINER, timeout=RESULTS_WAIT_TIMEOUT_MS)
        logger.info("IndiGo navigation: results container found.")
    except Exception:
        # Timed out — classify the failure.
        if await captcha_present(page):
            logger.warning("IndiGo navigation: CAPTCHA detected on results wait.")
            return WorkflowState.CAPTCHA_BLOCKED

        if await is_login_wall(page):
            logger.warning("IndiGo navigation: login wall detected.")
            return WorkflowState.AUTH_REQUIRED

        # Check for "no results" text in the body.
        try:
            body_text = (await page.locator("body").inner_text()).lower()
            for indicator in selectors.NO_RESULTS_INDICATORS:
                if indicator in body_text:
                    logger.info("IndiGo navigation: no results indicator found: '%s'", indicator)
                    return WorkflowState.NO_RESULTS
        except Exception:
            pass

        logger.error("IndiGo navigation: results did not appear — SEARCH_ERROR.")
        return WorkflowState.SEARCH_ERROR

    return WorkflowState.EXTRACT


# ---------------------------------------------------------------------------
# Top-level workflow runner
# ---------------------------------------------------------------------------

async def run_search_workflow(page, request: FareSearchRequest) -> WorkflowState:
    """
    Execute the complete IndiGo search workflow from OPEN_SOURCE through
    WAIT_RESULT_STATE. Returns the terminal WorkflowState for the caller
    (CollectionOrchestrator) to act on.

    This function never persists data, captures evidence, or retries.
    All those concerns belong in the orchestrator.

    Returns:
        WorkflowState.EXTRACT — success, ready for parser
        WorkflowState.CAPTCHA_BLOCKED — CAPTCHA detected, stop source
        WorkflowState.AUTH_REQUIRED — login wall detected, stop source
        WorkflowState.NO_RESULTS — no flights found for this search
        WorkflowState.SEARCH_ERROR — form/navigation error
        WorkflowState.SCHEMA_CHANGED — page structure doesn't match selectors
    """
    adults = request.passenger_count.adults

    # Ensure one-way is selected before filling the form.
    await select_one_way(page)

    for step, fn, args in [
        (WorkflowState.OPEN_SOURCE, open_source, (page,)),
        (WorkflowState.WAIT_PAGE_READY, wait_page_ready, (page,)),
        (WorkflowState.HANDLE_CONSENT, handle_consent, (page,)),
        (WorkflowState.ENTER_ORIGIN, enter_origin, (page, request.origin)),
        (WorkflowState.ENTER_DESTINATION, enter_destination, (page, request.destination)),
        (WorkflowState.SELECT_DATE, select_date, (page, request.travel_date)),
        (WorkflowState.SELECT_PASSENGERS, select_passengers, (page, adults)),
        (WorkflowState.SUBMIT_SEARCH, submit_search, (page,)),
        (WorkflowState.WAIT_RESULT_STATE, wait_result_state, (page,)),
    ]:
        logger.info("IndiGo workflow: executing state %s", step.value)
        result = await fn(*args)
        # Any state that isn't the expected *next* state is a terminal failure.
        if result not in (
            WorkflowState.WAIT_PAGE_READY,
            WorkflowState.HANDLE_CONSENT,
            WorkflowState.ENTER_ORIGIN,
            WorkflowState.ENTER_DESTINATION,
            WorkflowState.SELECT_DATE,
            WorkflowState.SELECT_PASSENGERS,
            WorkflowState.SUBMIT_SEARCH,
            WorkflowState.WAIT_RESULT_STATE,
            WorkflowState.EXTRACT,
        ):
            logger.warning(
                "IndiGo workflow: terminal failure state '%s' at step '%s'.",
                result.value, step.value,
            )
            return result

    return WorkflowState.EXTRACT
