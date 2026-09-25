"""
EaseMyTrip live source – Playwright + BeautifulSoup, compliance-gated.

Approach confirmed by prototype2 branch (apps/scraper/src/sources/easemytrip/).

KEY FINDING: The compliant host is `flight.easemytrip.com`, not `www.easemytrip.com`.
  - www.easemytrip.com/robots.txt  →  Disallow: /flight-search/listing*  (BLOCKED)
  - flight.easemytrip.com/robots.txt →  /FlightList/Index is NOT disallowed  (ALLOWED)

URL format (confirmed working in prototype2):
  https://flight.easemytrip.com/FlightList/Index
    ?srch={ORIGIN}-City|{DEST}-City|{DD/MM/YYYY}
    &px=1-0-0&cbn=0&CCode=IN&crn=INR

DOM selectors (confirmed by prototype2 parser.py):
  Card container  :  .nw_listing_bx
  Airline name    :  .air_nmm_txt h6
  Flight number   :  .air_nmm_txt span
  Price           :  h4[id^="spnPrice"]
  Stops           :  .tmln_rc  (text: "Non Stop" or "1 Stop")
  Results present :  .flt-res-card, .row.top-srh, .main-card, #row0

Navigation follows prototype2's state machine:
  LOAD_SEARCH_PAGE → PAGE_READY → WAIT_FOR_RESULTS → RESULTS_DETECTED | failure

Behaviour on failure:
  - robots.txt refusal    → return ([], refused_snapshot)
  - Protection/CAPTCHA    → stop, record reason, do not retry
  - HTTP 403 / 429        → stop, record reason, do not retry
  - No results / timeout  → return ([], snapshot) with body_path set
  - Network timeout       → one retry after 60 s, then stop
"""
from __future__ import annotations

import logging
import re
import time
from datetime import date, datetime
from pathlib import Path

from apix.compliance import ComplianceGate, Refused
from apix.models import Quote, RawSnapshot
from apix.sources.base import FareSource

logger = logging.getLogger(__name__)

_RAW_DIR = Path(__file__).parent.parent.parent.parent / "data" / "raw"

# ── Search host (compliance-verified 2026-09-25) ───────────────────────────
_SEARCH_HOST = "https://flight.easemytrip.com"
_SEARCH_PATH = "/FlightList/Index"

# Protection keywords that indicate a bot-detection page
_PROTECTION_KW = ("captcha", "verify you are human", "checking your browser", "security check")

# Wait for one of these selectors before parsing (condition-based, not sleep)
_RESULT_SELECTORS = ".flt-res-card, .row.top-srh, .main-card, #row0, .nw_listing_bx"

# How long to wait (ms) for the result selectors to appear
_RESULT_WAIT_MS = 60_000

# Small page-settle buffer (seconds) before checking the DOM for bot protection
_SETTLE_S = 5


def _build_url(origin: str, destination: str, travel_date: date) -> str:
    date_str = travel_date.strftime("%d/%m/%Y")
    srch = f"{origin}-City|{destination}-City|{date_str}"
    return f"{_SEARCH_HOST}{_SEARCH_PATH}?srch={srch}&px=1-0-0&cbn=0&CCode=IN&crn=INR"


def _is_protection_page(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in _PROTECTION_KW)


def _parse_price(text: str) -> float | None:
    cleaned = re.sub(r"[^\d.]", "", text)
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None


def _parse_stops(text: str) -> int:
    lower = text.lower()
    if "non" in lower:
        return 0
    m = re.search(r"(\d+)\s*stop", lower)
    return int(m.group(1)) if m else 0


def _assign_dep_band(dep_time: str | None) -> str | None:
    if not dep_time:
        return None
    try:
        hour = int(dep_time.split(":")[0])
    except (ValueError, AttributeError, IndexError):
        return None
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 18:
        return "afternoon"
    return "evening"


def _parse_html(
    html: str,
    route: str,
    origin: str,
    destination: str,
    travel_date: date,
    run_id: int,
    obs_date: date,
) -> list[Quote]:
    """
    Parse rendered flight-list HTML into Quote objects.

    Selectors confirmed by prototype2 apps/scraper/src/sources/easemytrip/parser.py:
      .nw_listing_bx        →  one flight card
      .air_nmm_txt h6       →  airline name
      .air_nmm_txt span     →  flight number
      h4[id^="spnPrice"]    →  total fare (₹ stripped)
      .tmln_rc              →  stop count text ("Non Stop", "1 Stop", ...)
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        raise RuntimeError(
            "beautifulsoup4 is not installed. Run: pip install beautifulsoup4"
        )

    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select(".nw_listing_bx")
    logger.info("EaseMyTrip: found %d flight cards for %s", len(cards), route)

    lead_days = (travel_date - obs_date).days
    quotes: list[Quote] = []

    for card in cards:
        try:
            airline_el    = card.select_one(".air_nmm_txt h6")
            flight_no_el  = card.select_one(".air_nmm_txt span")
            price_el      = card.select_one("h4[id^='spnPrice']")
            dep_time_el   = card.select_one(".tm_lc")       # first time block
            stops_el      = card.select_one(".tmln_rc")

            airline   = airline_el.get_text(strip=True)   if airline_el   else ""
            flight_no = flight_no_el.get_text(strip=True) if flight_no_el else None
            dep_time  = dep_time_el.get_text(strip=True)  if dep_time_el  else None
            stops_txt = stops_el.get_text(strip=True)     if stops_el     else "Non Stop"

            if not price_el:
                continue
            price_txt  = price_el.get_text(strip=True).replace(",", "").replace("₹", "").replace("Rs", "").strip()
            total_fare = _parse_price(price_txt)

            if not airline or total_fare is None:
                continue

            stops    = _parse_stops(stops_txt)
            dep_band = _assign_dep_band(dep_time)

            quotes.append(Quote(
                run_id=run_id,
                obs_date=obs_date,
                source="live",
                route=route,
                origin=origin,
                destination=destination,
                travel_date=travel_date,
                lead_days=lead_days,
                carrier=airline,
                flight_no=flight_no,
                dep_time=dep_time,
                dep_band=dep_band,
                stops=stops,
                fare_class="economy",
                base_fare=None,    # EMT shows only total fare on listing
                taxes=None,
                total_fare=total_fare,
                sold_out=False,
                parse_ok=True,
                anomaly_flag=False,
                is_synthetic=False,
            ))

        except Exception as exc:
            logger.warning("EaseMyTrip: error parsing card: %s", exc)
            continue

    return quotes


class EaseMyTripSource(FareSource):
    """
    Playwright scraper for flight.easemytrip.com.

    Uses the state-machine navigation approach from prototype2:
      LOAD_SEARCH_PAGE → PAGE_READY → WAIT_FOR_RESULTS → RESULTS_DETECTED
    Falls back to EMPTY_RESULTS / PROTECTION_DETECTED on failure.

    robots.txt compliance (checked 2026-09-25):
      flight.easemytrip.com/robots.txt does NOT disallow /FlightList/Index.
      ComplianceGate will allow these requests.
    """

    def __init__(
        self,
        run_id: int,
        compliance_gate: ComplianceGate,
        user_agent: str,
    ) -> None:
        self.run_id = run_id
        self.gate = compliance_gate
        self.user_agent = user_agent

    # ── Public ────────────────────────────────────────────────────────────

    def fetch(
        self,
        route: str,
        origin: str,
        destination: str,
        travel_date: date,
        run_id: int,
    ) -> tuple[list[Quote], RawSnapshot]:
        url = _build_url(origin, destination, travel_date)
        obs_date = datetime.utcnow().date()

        # ── Compliance gate ────────────────────────────────────────────────
        result = self.gate.check(url)
        if isinstance(result, Refused):
            logger.warning("EaseMyTrip: compliance refused %s — %s", url, result.reason)
            return [], RawSnapshot(
                run_id=run_id, route=route, travel_date=travel_date,
                fetched_at=datetime.utcnow(), url=url,
                http_status=None, robots_allowed=False, body_path=None,
            )

        # ── Playwright ────────────────────────────────────────────────────
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise RuntimeError(
                "playwright is not installed. Run:\n"
                "  pip install playwright && playwright install chromium"
            )

        http_status: int | None = None
        body_path: str | None = None
        quotes: list[Quote] = []

        def _do_fetch() -> tuple[int | None, str | None, list[Quote]]:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                ctx = browser.new_context(
                    user_agent=self.user_agent,
                    locale="en-IN",
                    timezone_id="Asia/Kolkata",
                )
                page = ctx.new_page()

                # ── State: LOAD_SEARCH_PAGE ────────────────────────────────
                logger.info("EaseMyTrip: navigating to %s", url)
                response = page.goto(url, timeout=45_000, wait_until="domcontentloaded")
                status = response.status if response else None

                if status in (403, 429):
                    logger.warning("EaseMyTrip: HTTP %s for %s — stopping", status, url)
                    browser.close()
                    return status, None, []

                # ── State: PAGE_READY — short settle before bot-check ──────
                time.sleep(_SETTLE_S)
                body_text = page.locator("body").inner_text()
                if _is_protection_page(body_text):
                    logger.warning("EaseMyTrip: bot protection detected for %s", url)
                    browser.close()
                    return status, None, []

                # ── State: WAIT_FOR_RESULTS (condition-based) ──────────────
                html: str | None = None
                try:
                    page.wait_for_selector(_RESULT_SELECTORS, timeout=_RESULT_WAIT_MS)
                    html = page.content()
                    logger.info("EaseMyTrip: results detected for %s", route)
                except Exception:
                    # Save whatever the page shows for debugging
                    html = page.content()
                    logger.warning("EaseMyTrip: no result selectors found for %s; saving raw HTML", route)

                # Re-check for protection after results wait
                if _is_protection_page(html):
                    logger.warning("EaseMyTrip: bot protection page after wait for %s", url)
                    browser.close()
                    return status, None, []

                # Save raw HTML
                _RAW_DIR.mkdir(parents=True, exist_ok=True)
                fname = (
                    f"emt_{route}_{travel_date}_"
                    f"{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}.html"
                )
                out_path = _RAW_DIR / fname
                out_path.write_text(html, encoding="utf-8")
                rel = str(out_path.relative_to(Path(__file__).parent.parent.parent.parent))

                parsed = _parse_html(
                    html, route, origin, destination, travel_date, run_id, obs_date
                )
                browser.close()
                return status, rel, parsed

        # One retry for network timeouts only
        for attempt in range(2):
            try:
                http_status, body_path, quotes = _do_fetch()
                break
            except Exception as exc:
                if attempt == 0 and "timeout" in str(exc).lower():
                    logger.warning(
                        "EaseMyTrip: network timeout for %s; retrying in 60 s", url
                    )
                    time.sleep(60)
                else:
                    logger.error("EaseMyTrip: fetch failed for %s: %s", url, exc)
                    break

        return quotes, RawSnapshot(
            run_id=run_id,
            route=route,
            travel_date=travel_date,
            fetched_at=datetime.utcnow(),
            url=url,
            http_status=http_status,
            robots_allowed=True,
            body_path=body_path,
        )
