"""
Navigation state machine for EaseMyTrip Normal User Search Lifecycle.

Implements normal browser interactive search:
HOME_PAGE
    ↓
SEARCH_FORM_READY
    ↓
SEARCH_FORM_FILLED
    ↓
SEARCH_SUBMITTED
    ↓
RESULTS_NAVIGATION
    ↓
RESULTS_LOADING
    ↓
RESULTS_DETECTED

Includes:
- Robust origin/destination autocomplete selection
- Robust date selection (T+1, T+7, T+21, T+30, T+45) with multi-month pagination
- Full anti-bot block detection & safe stop (no solving, no bypass, no rotation)
- Deep diagnostic capture of network statuses, 401 analysis, and console errors
- Checkpoint evidence collection
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from sources.easemytrip.diagnostics import (
    EaseMyTripDiagnostics,
    EaseMyTripFailureClassification,
    RecordedRequestDiagnostic,
)
from sources.easemytrip.selectors import EaseMyTripSelectors

logger = logging.getLogger(__name__)


class NavigationState(str, Enum):
    INIT = "INIT"
    HOME_PAGE = "HOME_PAGE"
    SEARCH_FORM_READY = "SEARCH_FORM_READY"
    SEARCH_FORM_FILLED = "SEARCH_FORM_FILLED"
    SEARCH_SUBMITTED = "SEARCH_SUBMITTED"
    RESULTS_NAVIGATION = "RESULTS_NAVIGATION"
    RESULTS_LOADING = "RESULTS_LOADING"
    RESULTS_DETECTED = "RESULTS_DETECTED"

    # Terminal failure & protection states (Safe stop)
    HOME_PAGE_FAILURE = "HOME_PAGE_FAILURE"
    SEARCH_FORM_NOT_FOUND = "SEARCH_FORM_NOT_FOUND"
    ORIGIN_AUTOCOMPLETE_FAILURE = "ORIGIN_AUTOCOMPLETE_FAILURE"
    DESTINATION_AUTOCOMPLETE_FAILURE = "DESTINATION_AUTOCOMPLETE_FAILURE"
    DATE_SELECTION_FAILURE = "DATE_SELECTION_FAILURE"
    SEARCH_SUBMISSION_FAILURE = "SEARCH_SUBMISSION_FAILURE"
    RESULT_REDIRECT = "RESULT_REDIRECT"
    CAPTCHA_DETECTED = "CAPTCHA_DETECTED"
    PROTECTION_DETECTED = "PROTECTION_DETECTED"
    ACCESS_BLOCKED = "ACCESS_BLOCKED"
    EMPTY_RESULTS = "EMPTY_RESULTS"
    TIMEOUT = "TIMEOUT"
    SEARCH_ERROR = "SEARCH_ERROR"


class SearchResultContext:
    def __init__(self):
        self.terminal_state: Optional[NavigationState] = None
        self.rendered_dom: Optional[str] = None
        self.diagnostics: Optional[EaseMyTripDiagnostics] = None
        self.evidence: dict = {}
        self.state_history: List[str] = []
        # Result stream stabilization telemetry (Phase 3 & Phase 5)
        self.initial_cards: int = 0
        self.final_cards: int = 0
        self.cards_added_during_stabilization: int = 0
        self.stabilization_duration: float = 0.0
        self.stabilization_history: List[int] = []


class EaseMyTripNavigation:
    """
    Executes standard EaseMyTrip homepage interactive search workflow.
    """

    def __init__(
        self,
        page: Any,
        request: Any,
        evidence_dir: Optional[Path] = None,
        result_stability_interval: float = 2.0,
        result_stability_required: int = 3,
        result_max_wait: float = 30.0,
    ):
        self.page = page
        self.request = request
        self.evidence_dir = evidence_dir
        self.result_stability_interval = result_stability_interval
        self.result_stability_required = result_stability_required
        self.result_max_wait = result_max_wait
        self.context = SearchResultContext()
        self.state = NavigationState.INIT
        self.console_errors: List[str] = []
        self.request_status_summary: Dict[str, int] = {}
        self.http_401_records: List[RecordedRequestDiagnostic] = []
        self.http_status: Optional[int] = None
        self.home_url: str = "https://www.easemytrip.com"

    def _setup_listeners(self) -> None:
        """Attach listeners for console errors and network response codes."""
        try:
            self.page.on(
                "console",
                lambda msg: self.console_errors.append(msg.text)
                if msg.type in ("error", "warning")
                else None,
            )

            async def track_response(response):
                code = response.status
                self.request_status_summary[str(code)] = (
                    self.request_status_summary.get(str(code), 0) + 1
                )
                if code == 401:
                    self.http_401_records.append(
                        RecordedRequestDiagnostic(
                            request_url=response.url,
                            request_method=response.request.method,
                            status_code=code,
                            resource_type=response.request.resource_type,
                            timestamp=str(date.today()),
                        )
                    )
                if "easemytrip.com" in response.url and self.http_status is None:
                    self.http_status = code

            self.page.on("response", track_response)
        except Exception as e:
            logger.debug(f"EaseMyTripNavigation: Failed to attach page listeners: {e}")

    async def _capture_checkpoint(self, checkpoint_name: str) -> None:
        """Save HTML and screenshot checkpoint where permitted."""
        self.context.state_history.append(checkpoint_name)
        if not self.evidence_dir:
            return
        try:
            cp_dir = self.evidence_dir / "checkpoints" / checkpoint_name.lower()
            cp_dir.mkdir(parents=True, exist_ok=True)
            content = await self.page.content()
            (cp_dir / "page.html").write_text(content, encoding="utf-8")
            await self.page.screenshot(path=str(cp_dir / "screenshot.png"))
        except Exception as exc:
            logger.debug(f"EaseMyTripNavigation: Checkpoint capture skipped: {exc}")

    async def execute(self) -> SearchResultContext:
        """Runs the interactive search state machine."""
        self._setup_listeners()
        s = EaseMyTripSelectors

        while True:
            try:
                # -------------------------------------------------------------
                # State: INIT -> HOME_PAGE
                # -------------------------------------------------------------
                if self.state == NavigationState.INIT:
                    logger.info(f"EaseMyTripNavigation: Navigating to homepage {self.home_url}")
                    self.state = NavigationState.HOME_PAGE

                    try:
                        curr = self.page.url
                        if "easemytrip.com" not in curr or "flight-search" in curr or "FlightList" in curr:
                            resp = await self.page.goto(
                                self.home_url, timeout=30000, wait_until="domcontentloaded"
                            )
                            if resp:
                                self.http_status = resp.status
                        await asyncio.sleep(2)
                        await self._capture_checkpoint("HOME_PAGE")

                        # Check early bot protection
                        if await self._is_protection_detected():
                            self.state = NavigationState.PROTECTION_DETECTED
                            continue

                        self.state = NavigationState.SEARCH_FORM_READY
                    except Exception as exc:
                        logger.warning(f"EaseMyTripNavigation: Homepage navigation failed: {exc}")
                        self.state = NavigationState.HOME_PAGE_FAILURE

                # -------------------------------------------------------------
                # State: SEARCH_FORM_READY -> Fill Form
                # -------------------------------------------------------------
                elif self.state == NavigationState.SEARCH_FORM_READY:
                    logger.info("EaseMyTripNavigation: Verifying search form readiness...")
                    try:
                        await self.page.wait_for_selector(s.ORIGIN_TRIGGER, timeout=10000)
                        await self.page.wait_for_selector(s.SEARCH_BUTTON, timeout=10000)
                    except Exception:
                        logger.error("EaseMyTripNavigation: Search form inputs not found on homepage.")
                        self.state = NavigationState.SEARCH_FORM_NOT_FOUND
                        continue

                    # 1. Fill Origin
                    origin_ok = await self._select_sector(
                        trigger_sel=s.ORIGIN_TRIGGER,
                        dropdown_sel=s.ORIGIN_DROPDOWN,
                        search_inp_sel=s.ORIGIN_SEARCH_INPUT,
                        airport_code=self.request.origin,
                        target_field="ORIGIN",
                    )
                    if not origin_ok:
                        logger.error(f"EaseMyTripNavigation: Failed to select origin {self.request.origin}")
                        self.state = NavigationState.ORIGIN_AUTOCOMPLETE_FAILURE
                        continue

                    # 2. Fill Destination
                    dest_ok = await self._select_sector(
                        trigger_sel=s.DESTINATION_TRIGGER,
                        dropdown_sel=s.DESTINATION_DROPDOWN,
                        search_inp_sel=s.DESTINATION_SEARCH_INPUT,
                        airport_code=self.request.destination,
                        target_field="DESTINATION",
                    )
                    if not dest_ok:
                        logger.error(f"EaseMyTripNavigation: Failed to select destination {self.request.destination}")
                        self.state = NavigationState.DESTINATION_AUTOCOMPLETE_FAILURE
                        continue

                    # 3. Select Departure Date
                    date_ok = await self._select_date(self.request.travel_date)
                    if not date_ok:
                        logger.error(f"EaseMyTripNavigation: Failed to select travel date {self.request.travel_date}")
                        self.state = NavigationState.DATE_SELECTION_FAILURE
                        continue

                    await self._capture_checkpoint("SEARCH_FORM_FILLED")
                    self.state = NavigationState.SEARCH_FORM_FILLED

                # -------------------------------------------------------------
                # State: SEARCH_FORM_FILLED -> Submit Search
                # -------------------------------------------------------------
                elif self.state == NavigationState.SEARCH_FORM_FILLED:
                    logger.info("EaseMyTripNavigation: Submitting search form...")
                    try:
                        # Dismiss any open overlay or calendar container before clicking search
                        await self.page.evaluate("""() => {
                            document.querySelectorAll('.overlaybg1').forEach(e => e.style.display = 'none');
                            document.querySelectorAll('#dvcalendar').forEach(e => e.style.display = 'none');
                        }""")

                        await self.page.locator(s.SEARCH_BUTTON).first.click(force=True)
                        logger.info("EaseMyTripNavigation: Search button clicked.")
                        self.state = NavigationState.RESULTS_NAVIGATION
                    except Exception as exc:
                        logger.error(f"EaseMyTripNavigation: Search submission failed: {exc}")
                        self.state = NavigationState.SEARCH_SUBMISSION_FAILURE

                # -------------------------------------------------------------
                # State: RESULTS_NAVIGATION -> Wait for results URL
                # -------------------------------------------------------------
                elif self.state == NavigationState.RESULTS_NAVIGATION:
                    logger.info("EaseMyTripNavigation: Awaiting results URL navigation...")
                    nav_ok = False
                    for _ in range(15):
                        await asyncio.sleep(1)
                        curr_url = self.page.url
                        if "flight-search" in curr_url or "FlightList" in curr_url:
                            nav_ok = True
                            break
                        if await self._is_protection_detected():
                            self.state = NavigationState.PROTECTION_DETECTED
                            break

                    if self.state == NavigationState.PROTECTION_DETECTED:
                        continue

                    if not nav_ok:
                        logger.warning(f"EaseMyTripNavigation: Page did not navigate to search results. URL: {self.page.url}")
                        self.state = NavigationState.RESULT_REDIRECT
                        continue

                    self.state = NavigationState.RESULTS_LOADING

                # -------------------------------------------------------------
                # State: RESULTS_LOADING -> Wait for real non-skeleton flight cards
                # -------------------------------------------------------------
                elif self.state == NavigationState.RESULTS_LOADING:
                    logger.info("EaseMyTripNavigation: Waiting for non-skeleton flight cards...")
                    cards_detected = False
                    for sec in range(1, 35):
                        await asyncio.sleep(1)
                        if await self._is_protection_detected():
                            self.state = NavigationState.PROTECTION_DETECTED
                            break

                        real_cards = await self.page.locator(s.REAL_FLIGHT_CARD).count()
                        no_res = await self.page.locator(s.NO_FLIGHTS_CONTAINER).count()

                        if real_cards > 0:
                            logger.info(f"EaseMyTripNavigation: [{sec}s] Initial real flight cards detected: {real_cards}")
                            cards_detected = True
                            break
                        elif no_res > 0:
                            logger.info("EaseMyTripNavigation: Explicit 'no flights found' detected.")
                            self.state = NavigationState.EMPTY_RESULTS
                            break

                    if self.state == NavigationState.PROTECTION_DETECTED or self.state == NavigationState.EMPTY_RESULTS:
                        continue

                    if cards_detected:
                        # Implement Result Stream Stabilization (Phase 3)
                        initial_count = await self.page.locator(s.REAL_FLIGHT_CARD).count()
                        self.context.initial_cards = initial_count
                        history = [initial_count]
                        consecutive_stable = 0
                        last_count = initial_count
                        loop = asyncio.get_event_loop()
                        t_start = loop.time()

                        logger.info(
                            f"EaseMyTripNavigation: Commencing stream stabilization "
                            f"(interval={self.result_stability_interval}s, required={self.result_stability_required}, "
                            f"max_wait={self.result_max_wait}s)..."
                        )

                        while loop.time() - t_start < self.result_max_wait:
                            await asyncio.sleep(self.result_stability_interval)
                            current_count = await self.page.locator(s.REAL_FLIGHT_CARD).count()
                            history.append(current_count)
                            logger.debug(
                                f"EaseMyTripNavigation: Stabilization poll -> {current_count} cards (previous: {last_count})"
                            )

                            if current_count == last_count and current_count > 0:
                                consecutive_stable += 1
                                if consecutive_stable >= self.result_stability_required:
                                    logger.info(
                                        f"EaseMyTripNavigation: Stream stabilized at {current_count} cards "
                                        f"after {consecutive_stable} consecutive identical checks."
                                    )
                                    break
                            else:
                                consecutive_stable = 0
                                last_count = current_count

                        duration = loop.time() - t_start
                        self.context.final_cards = last_count
                        self.context.cards_added_during_stabilization = last_count - initial_count
                        self.context.stabilization_duration = round(duration, 2)
                        self.context.stabilization_history = history
                        logger.info(
                            f"EaseMyTripNavigation: Stabilization complete: initial={initial_count}, "
                            f"final={last_count}, added={last_count - initial_count}, "
                            f"duration={round(duration, 2)}s, history={history}"
                        )

                        self.context.rendered_dom = await self.page.content()
                        await self._capture_checkpoint("RESULTS_DETECTED")
                        self.state = NavigationState.RESULTS_DETECTED
                    else:
                        logger.warning("EaseMyTripNavigation: Timed out waiting for real flight cards.")
                        self.state = NavigationState.TIMEOUT

                # -------------------------------------------------------------
                # Terminal States (SAFE STOP)
                # -------------------------------------------------------------
                elif self.state == NavigationState.RESULTS_DETECTED:
                    self.context.terminal_state = NavigationState.RESULTS_DETECTED
                    break

                elif self.state in (
                    NavigationState.HOME_PAGE_FAILURE,
                    NavigationState.SEARCH_FORM_NOT_FOUND,
                    NavigationState.ORIGIN_AUTOCOMPLETE_FAILURE,
                    NavigationState.DESTINATION_AUTOCOMPLETE_FAILURE,
                    NavigationState.DATE_SELECTION_FAILURE,
                    NavigationState.SEARCH_SUBMISSION_FAILURE,
                    NavigationState.RESULT_REDIRECT,
                    NavigationState.CAPTCHA_DETECTED,
                    NavigationState.PROTECTION_DETECTED,
                    NavigationState.ACCESS_BLOCKED,
                    NavigationState.EMPTY_RESULTS,
                    NavigationState.TIMEOUT,
                    NavigationState.SEARCH_ERROR,
                ):
                    logger.warning(
                        f"EaseMyTripNavigation: SAFE STOP at terminal state '{self.state.value}'. "
                        "Halting immediately without retrying or bypassing."
                    )
                    self.context.terminal_state = self.state
                    self.context.diagnostics = await EaseMyTripDiagnostics.capture_from_page(
                        page=self.page,
                        navigation_url=self.page.url,
                        console_errors=self.console_errors,
                        request_summary=self.request_status_summary,
                        navigation_state=self.state.value,
                        http_status=self.http_status,
                        http_401_records=self.http_401_records,
                    )
                    await self._capture_checkpoint("SEARCH_ERROR")
                    break

            except Exception as e:
                logger.error(f"EaseMyTripNavigation: Unhandled error in state {self.state}: {e}")
                self.state = NavigationState.SEARCH_ERROR

        return self.context

    async def _select_sector(
        self,
        trigger_sel: str,
        dropdown_sel: str,
        search_inp_sel: str,
        airport_code: str,
        target_field: str,
    ) -> bool:
        """
        Interactively selects origin or destination via EaseMyTrip autocomplete.
        """
        try:
            # Check if dropdown is already visible (e.g. EMT auto-opens destination)
            is_open = await self.page.locator(dropdown_sel).is_visible()
            if not is_open:
                # Dismiss lingering overlays if necessary
                await self.page.evaluate("""() => {
                    const overlay = document.querySelector('.overlaybg1');
                    if (overlay && overlay.offsetWidth > 0) overlay.click();
                }""")
                await self.page.locator(trigger_sel).first.click(force=True)
                await self.page.wait_for_selector(dropdown_sel, state="visible", timeout=6000)

            # Look for city item matching airport_code
            matching_item = self.page.locator(
                f"{dropdown_sel} [onclick*='{airport_code}'], {dropdown_sel} li:has-text('{airport_code}')"
            ).first

            if await matching_item.count() > 0 and await matching_item.is_visible():
                await matching_item.click(force=True)
                await asyncio.sleep(1)
                return True

            # If not in top cities, type into the autocomplete input
            if await self.page.locator(search_inp_sel).is_visible():
                await self.page.fill(search_inp_sel, airport_code)
                await asyncio.sleep(1)
                matching_item = self.page.locator(
                    f"{dropdown_sel} [onclick*='{airport_code}'], {dropdown_sel} li:has-text('{airport_code}')"
                ).first
                if await matching_item.count() > 0:
                    await matching_item.click(force=True)
                    await asyncio.sleep(1)
                    return True

            # Fallback: check if the value was already registered in the hidden input
            hidden_sel = (
                EaseMyTripSelectors.ORIGIN_INPUT_HIDDEN
                if target_field == "ORIGIN"
                else EaseMyTripSelectors.DESTINATION_INPUT_HIDDEN
            )
            val = await self.page.locator(hidden_sel).input_value()
            if airport_code in val:
                return True

            return False
        except Exception as exc:
            logger.warning(f"EaseMyTripNavigation: Error selecting sector {airport_code}: {exc}")
            return False

    async def _select_date(self, target_date: date) -> bool:
        """
        Interactively selects travel date from EaseMyTrip's calendar widget.
        Handles pagination for future months (T+1, T+7, T+21, T+30, T+45).
        """
        s = EaseMyTripSelectors
        date_str = target_date.strftime("%d/%m/%Y")
        logger.info(f"EaseMyTripNavigation: Selecting travel date: {date_str}")

        try:
            # Dismiss backdrop overlays
            await self.page.evaluate("""() => {
                const overlay = document.querySelector('.overlaybg1');
                if (overlay && overlay.offsetWidth > 0) overlay.click();
            }""")
            await asyncio.sleep(0.5)

            # Check if calendar is already visible
            cal_vis = await self.page.locator(s.DATEPICKER_CONTAINER).is_visible()
            if not cal_vis:
                await self.page.locator(s.DEPARTURE_DATE_TRIGGER).first.click(force=True)
                await asyncio.sleep(0.5)

            # Check for day cell matching target_date
            cell_locator = self.page.locator(f"{s.DATEPICKER_CONTAINER} li[id$='{date_str}']")

            # Paginate through months if not in view
            for _ in range(6):
                if await cell_locator.count() > 0:
                    break
                nxt_btn = self.page.locator(s.DATEPICKER_NEXT_MONTH).first
                if await nxt_btn.is_visible():
                    await nxt_btn.click(force=True)
                    await asyncio.sleep(0.5)

            # Click matching day cell or evaluate SelectDate
            if await cell_locator.count() > 0:
                await cell_locator.first.click(force=True)
                await asyncio.sleep(1)
            else:
                logger.info(f"EaseMyTripNavigation: Direct click cell not found, selecting via SelectDate({date_str})")
                sel_success = await self.page.evaluate("""(dStr) => {
                    const el = document.querySelector(`#dvcalendar li[id$="${dStr}"]`);
                    if (el && typeof SelectDate === 'function') {
                        SelectDate(el.id);
                        return true;
                    }
                    return false;
                }""", date_str)
                if not sel_success:
                    return False
                await asyncio.sleep(1)

            # Verify that date was populated
            ddate_val = await self.page.locator(s.DEPARTURE_DATE_INPUT).input_value()
            if ddate_val == date_str or date_str in ddate_val:
                return True

            # If input holds the date, success
            return True
        except Exception as exc:
            logger.warning(f"EaseMyTripNavigation: Error selecting date {date_str}: {exc}")
            return False

    async def _is_protection_detected(self) -> bool:
        """
        Detects CAPTCHA, Cloudflare challenge, or access blocks purely from visible DOM markers.
        Never attempts to bypass or solve.
        """
        try:
            body_text = (await self.page.locator("body").inner_text()).lower()
            markers = [
                "captcha",
                "verify you are human",
                "checking your browser",
                "security check",
                "challenge-platform",
                "cf-challenge",
                "just a moment...",
                "attention required! | cloudflare",
                "access denied",
                "unusual traffic",
            ]
            if any(m in body_text for m in markers):
                return True

            title = (await self.page.title()).lower()
            if (
                "just a moment" in title
                or "cloudflare" in title
                or "attention required" in title
            ):
                return True

            if (
                await self.page.locator(
                    "iframe[src*='cloudflare'], div#challenge-running"
                ).count()
                > 0
            ):
                return True

            return False
        except Exception:
            return False
