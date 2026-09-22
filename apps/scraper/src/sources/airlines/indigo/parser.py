"""
parser.py — IndiGo results page extractor.

Extraction priority (spec §extraction-priority):
  1. Public structured JSON delivered to browser (via page.expect_response)
  2. Semantic DOM using stable selectors from selectors.py

The parser receives the Playwright page object (after results have loaded)
and returns a list of raw dicts — one per fare card. The normalizer then
converts these into FareObservation fields.

This module must NOT:
  - Make any HTTP requests directly
  - Write to any storage
  - Apply any normalization (that is normalizer.py's job)
  - Return None silently — if parsing fails, raise ParserError with reason
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from . import selectors

logger = logging.getLogger(__name__)

PARSER_VERSION = "1.0.0"


class ParserError(Exception):
    """
    Raised when the parser cannot extract expected data.
    Caller (orchestrator) maps this to WorkflowState.SCHEMA_CHANGED.
    """
    pass


async def extract_from_network_response(
    intercepted_json: Optional[dict],
) -> list[dict[str, Any]]:
    """
    Parse the structured JSON that IndiGo's app loads from its search API.
    This is the preferred extraction path: the browser fetches structured
    data openly, and we simply read what was delivered to the page.

    Args:
        intercepted_json: The parsed JSON body of the flight search API response.

    Returns:
        List of raw fare dicts, one per card.
        Returns [] if no fares found (caller maps to NO_RESULTS).
    """
    if not intercepted_json:
        return []

    raw_fares = []

    # IndiGo's API typically returns data in one of these shapes.
    # We try each key path and take the first one that yields a list.
    candidate_paths = [
        ["data", "flights"],
        ["data", "results"],
        ["flights"],
        ["results"],
        ["flightResults"],
        ["data"],
    ]

    flight_list = None
    for path in candidate_paths:
        node = intercepted_json
        try:
            for key in path:
                node = node[key]
            if isinstance(node, list) and len(node) > 0:
                flight_list = node
                logger.info("parser: found %d flights at path %s.", len(node), path)
                break
        except (KeyError, TypeError):
            continue

    if not flight_list:
        logger.info("parser: network JSON yielded no recognisable flight list.")
        return []

    for item in flight_list:
        # Extract fields defensively — missing fields become None (not ParserError).
        raw_fare = {
            "flight_number": _dig(item, ["flightNumber", "flight_number", "number"]),
            "departure_time": _dig(item, ["departureTime", "departure_time", "departs"]),
            "arrival_time": _dig(item, ["arrivalTime", "arrival_time", "arrives"]),
            "duration": _dig(item, ["duration", "flightDuration"]),
            "stops": _dig(item, ["stops", "numberOfStops", "no_of_stops"]),
            "fare_class": _dig(item, ["fareClass", "bookingClass", "fare_class"]),
            "fare_family": _dig(item, ["fareFamily", "fareType", "fare_family"]),
            "base_fare": _dig(item, ["baseFare", "base_fare", "basePrice"]),
            "taxes": _dig(item, ["taxes", "tax", "taxAmount"]),
            "total_fare": _dig(item, ["totalFare", "total_fare", "totalPrice", "price", "amount"]),
            "currency": _dig(item, ["currency"]) or "INR",
            "source_offer_id": _dig(item, ["offerId", "itineraryId", "id"]),
            "_raw": item,  # Preserve original for audit
        }
        raw_fares.append(raw_fare)

    return raw_fares


async def extract_from_dom(page) -> list[dict[str, Any]]:
    """
    Fallback extraction path: read fare cards directly from the rendered DOM.
    Used when no clean network JSON was intercepted.

    Returns:
        List of raw fare dicts (keys match extract_from_network_response output).
    """
    logger.info("parser: falling back to DOM extraction.")

    try:
        cards = page.locator(selectors.FLIGHT_CARD)
        card_count = await cards.count()
        logger.info("parser: found %d flight cards in DOM.", card_count)
    except Exception as exc:
        raise ParserError(f"Could not locate flight cards: {exc}")

    if card_count == 0:
        # Double-check for no-results text before raising.
        try:
            body = (await page.locator("body").inner_text()).lower()
            for indicator in selectors.NO_RESULTS_INDICATORS:
                if indicator in body:
                    logger.info("parser: no-results indicator in DOM body.")
                    return []
        except Exception:
            pass
        logger.info("parser: DOM has no flight cards — likely NO_RESULTS.")
        return []

    raw_fares = []
    for i in range(card_count):
        card = cards.nth(i)
        try:
            raw_fare = {
                "flight_number": await _safe_text(card, selectors.FLIGHT_NUMBER),
                "departure_time": await _safe_text(card, selectors.DEPARTURE_TIME),
                "arrival_time": await _safe_text(card, selectors.ARRIVAL_TIME),
                "duration": await _safe_text(card, selectors.DURATION_ELEMENT),
                "stops": await _safe_text(card, selectors.STOPS_ELEMENT),
                "fare_class": await _safe_text(card, selectors.FARE_CLASS),
                "fare_family": None,
                "base_fare": None,       # IndiGo DOM usually shows total only
                "taxes": None,
                "total_fare": await _safe_text(card, selectors.PRICE_ELEMENT),
                "currency": "INR",
                "source_offer_id": None,
                "_raw": None,
            }
            raw_fares.append(raw_fare)
        except Exception as exc:
            logger.warning("parser: failed to parse card %d — %s", i, exc)
            continue

    return raw_fares


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dig(obj: Any, keys: list[str]) -> Optional[Any]:
    """Try multiple key names on a dict and return the first hit."""
    if not isinstance(obj, dict):
        return None
    for key in keys:
        val = obj.get(key)
        if val is not None:
            return val
    return None


async def _safe_text(locator, selector: str) -> Optional[str]:
    """Return the inner text of the first matching child element, or None."""
    try:
        el = locator.locator(selector).first
        if await el.count() > 0:
            return (await el.inner_text()).strip() or None
    except Exception:
        pass
    return None
