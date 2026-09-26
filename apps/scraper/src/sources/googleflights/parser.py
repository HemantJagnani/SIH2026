"""
DOM Parser for Google Flights.
Extracts flights from the rendered DOM without relying on obfuscated CSS classes.
Enforces Phase 7 (Core Scan), Phase 8 (Flight Number Resolution),
Phase 10 (Price Semantics), and Phase 20 (No Fabrication).
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, time, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID
from bs4 import BeautifulSoup, Tag

from models.request import FareSearchRequest
from models.provenance import FieldStatus, MissingReason
from models.itinerary import PriceStatus
from sources.googleflights.flight_number_resolver import FlightNumberResolver
from sources.googleflights.selectors import GoogleFlightsSelectors

logger = logging.getLogger(__name__)


def parse_dom(
    html_content: str,
    request: FareSearchRequest,
    run_id: UUID,
    source_id: str,
    source_url: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Parse Google Flights DOM and return raw fare dictionaries for the core scan.
    """
    raw_fares: List[Dict[str, Any]] = []

    if not html_content:
        logger.warning("Empty HTML content provided to Google Flights parser.")
        return raw_fares

    soup = BeautifulSoup(html_content, "html.parser")
    list_items = soup.find_all('li')

    cards_detected = 0
    cards_parsed = 0
    cards_rejected = 0
    rank = 1

    for li in list_items:
        text = li.get_text(separator=" | ", strip=True)

        # A valid flight card should have time indicators and currency indicators
        if ("AM" in text or "PM" in text or ":" in text) and ("₹" in text or "INR" in text):
            cards_detected += 1

            # Determine category (BEST, OTHER, CHEAPEST) from preceding headings/structure
            category = _detect_google_category(li)

            try:
                raw_fare = _extract_flight_data(
                    card=li,
                    text=text,
                    request=request,
                    run_id=run_id,
                    source_id=source_id,
                    source_url=source_url,
                    category=category,
                    rank=rank,
                )
                if raw_fare:
                    raw_fares.append(raw_fare)
                    cards_parsed += 1
                    rank += 1
                else:
                    cards_rejected += 1
            except Exception as e:
                logger.debug(f"Failed to parse flight card: {e}")
                cards_rejected += 1

    logger.info(
        f"Google Flights Parser Diagnostics: detected={cards_detected}, "
        f"parsed={cards_parsed}, rejected={cards_rejected}"
    )
    return raw_fares


def parse_expanded_cards(
    htmls: List[str],
    request: FareSearchRequest,
    run_id: UUID,
    source_id: str,
    source_url: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Parse a list of HTML blocks representing expanded flight cards.
    Extracts core details plus legitimate flight segments and explicit baggage numbers.
    NEVER fabricates missing baggage or missing flight numbers.
    """
    raw_fares = []
    rank = 1

    for html in htmls:
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator=" | ", strip=True)

        category = _detect_google_category(soup)
        raw_fare = _extract_flight_data(
            card=soup,
            text=text,
            request=request,
            run_id=run_id,
            source_id=source_id,
            source_url=source_url,
            category=category,
            rank=rank,
            expanded_soup=soup,
        )
        if not raw_fare:
            continue

        rank += 1

        # Legitimate baggage extraction from text: only if explicit kg number is stated
        cabin_baggage = None
        checkin_baggage = None

        # Check for explicit numbers like "7 kg" or "15 kg"
        cabin_match = re.search(r'(?:carry[- ]on|cabin)[^0-9\n\r]*?(\d+)\s*(?:kg|kilos)', text, re.IGNORECASE)
        if cabin_match:
            cabin_baggage = int(cabin_match.group(1))

        checkin_match = re.search(r'(?:check(?:ed|[- ]in))[^0-9\n\r]*?(\d+)\s*(?:kg|kilos)', text, re.IGNORECASE)
        if checkin_match:
            checkin_baggage = int(checkin_match.group(1))

        # Check provenance for baggage
        prov = raw_fare.get("field_provenance", {})
        if cabin_baggage is not None:
            prov["cabin_baggage_kg"] = {
                "status": FieldStatus.OBSERVED.value,
                "source": "GOOGLE_EXPANDED_DETAILS",
                "missing_reason": None,
            }
        else:
            prov["cabin_baggage_kg"] = {
                "status": FieldStatus.UNAVAILABLE.value,
                "source": None,
                "missing_reason": MissingReason.NOT_PRESENT_AFTER_EXPANSION.value,
            }

        if checkin_baggage is not None:
            prov["checkin_baggage_kg"] = {
                "status": FieldStatus.OBSERVED.value,
                "source": "GOOGLE_EXPANDED_DETAILS",
                "missing_reason": None,
            }
        else:
            prov["checkin_baggage_kg"] = {
                "status": FieldStatus.UNAVAILABLE.value,
                "source": None,
                "missing_reason": MissingReason.NOT_PRESENT_AFTER_EXPANSION.value,
            }

        raw_fare["cabin_baggage_kg"] = cabin_baggage
        raw_fare["checkin_baggage_kg"] = checkin_baggage

        # Flight segments
        flight_segments = []
        flight_num = raw_fare.get("flight_number")
        if raw_fare.get("stops") == 0:
            flight_segments.append({
                "segment_number": 1,
                "origin": request.origin,
                "destination": request.destination,
                "flight_number": flight_num or "UNKNOWN",
                "operating_carrier": raw_fare.get("airline", "UNKNOWN"),
                "departure_time": raw_fare.get("departure_time_local"),
                "arrival_time": raw_fare.get("arrival_time_local"),
                "duration": None,
            })
        raw_fare["flight_segments"] = flight_segments

        raw_fares.append(raw_fare)

    return raw_fares


def _detect_google_category(element: Tag | BeautifulSoup) -> Optional[str]:
    """
    Detect Google Flights category: BEST, OTHER, CHEAPEST.
    """
    # Check parent/ancestor headings or container attributes
    curr = element
    for _ in range(6):
        if not curr or not hasattr(curr, "parent"):
            break
        curr = curr.parent
        if not curr:
            break
        # Look for preceding headings in the same container
        prev_heading = curr.find_previous(["h2", "h3", "h4", "div"])
        if prev_heading:
            h_text = prev_heading.get_text(strip=True).lower()
            if "top departing" in h_text or "best departing" in h_text or "best flight" in h_text:
                return "BEST"
            if "other departing" in h_text or "other flight" in h_text:
                return "OTHER"
            if "cheapest" in h_text:
                return "CHEAPEST"

    return None


def _extract_flight_data(
    card: Tag | BeautifulSoup,
    text: str,
    request: FareSearchRequest,
    run_id: UUID,
    source_id: str,
    source_url: Optional[str] = None,
    category: Optional[str] = None,
    rank: Optional[int] = None,
    expanded_soup: Optional[Tag | BeautifulSoup] = None,
) -> Optional[Dict[str, Any]]:
    """
    Extract individual fields strictly per specifications.
    Never fabricates tax, fees, baggage, or flight numbers.
    """
    # 1. Price Extraction
    price_match = re.search(r'₹\s*([\d,]+)', text)
    if not price_match:
        return None

    price_raw = price_match.group(0)
    try:
        total_fare_val = float(price_match.group(1).replace(",", ""))
    except ValueError:
        return None

    # Determine price status
    price_status = PriceStatus.DISPLAYED_TOTAL
    if "from" in text.lower() or "starts at" in text.lower():
        price_status = PriceStatus.DISPLAYED_FROM

    # 2. Times Extraction
    time_matches = re.findall(r'(\d{1,2}:\d{2}\s*(?:AM|PM))', text)
    unique_times = []
    for tm in time_matches:
        if tm not in unique_times:
            unique_times.append(tm)

    departure_time_local = None
    arrival_time_local = None

    if len(unique_times) >= 2:
        dep_str = unique_times[0].replace('\u202f', ' ').replace('\xa0', ' ')
        arr_str = unique_times[1].replace('\u202f', ' ').replace('\xa0', ' ')
        try:
            dep_t = datetime.strptime(dep_str, "%I:%M %p").time()
            arr_t = datetime.strptime(arr_str, "%I:%M %p").time()
            departure_time_local = datetime.combine(request.travel_date, dep_t).isoformat()
            arrival_time_local = datetime.combine(request.travel_date, arr_t).isoformat()
        except Exception:
            pass

    # 3. Airline Extraction
    airline = "Unknown"
    snippets = [s.strip() for s in text.split(" | ") if s.strip()]
    for snippet in snippets:
        if (
            len(snippet) > 2
            and not re.search(r'\d', snippet)
            and "stop" not in snippet.lower()
            and "min" not in snippet.lower()
            and "hr" not in snippet.lower()
            and "flight" not in snippet.lower()
            and "included" not in snippet.lower()
            and "deal" not in snippet.lower()
        ):
            airline = snippet
            break

    # 4. Stops
    stops = 0
    if "non-stop" in text.lower() or "direct" in text.lower():
        stops = 0
    else:
        stop_match = re.search(r'(\d+)\s*stop', text.lower())
        if stop_match:
            stops = int(stop_match.group(1))

    # 5. Flight Number Resolution (Phase 8)
    fn_resolution = FlightNumberResolver.resolve(card, expanded_soup=expanded_soup)
    flight_number = fn_resolution.flight_number

    # 6. Provenance Tracking (Phase 3)
    field_provenance: Dict[str, Any] = {
        "total_fare": {
            "status": FieldStatus.OBSERVED.value,
            "source": "GOOGLE_RESULT_CARD",
            "missing_reason": None,
        },
        "base_fare": {
            "status": FieldStatus.UNAVAILABLE.value,
            "source": None,
            "missing_reason": MissingReason.SOURCE_TOTAL_ONLY.value,
        },
        "taxes": {
            "status": FieldStatus.UNAVAILABLE.value,
            "source": None,
            "missing_reason": MissingReason.SOURCE_TOTAL_ONLY.value,
        },
        "gst": {
            "status": FieldStatus.UNAVAILABLE.value,
            "source": None,
            "missing_reason": MissingReason.SOURCE_TOTAL_ONLY.value,
        },
        "fees": {
            "status": FieldStatus.UNAVAILABLE.value,
            "source": None,
            "missing_reason": MissingReason.SOURCE_TOTAL_ONLY.value,
        },
        "flight_number": {
            "status": FieldStatus.OBSERVED.value if flight_number else FieldStatus.UNAVAILABLE.value,
            "source": fn_resolution.resolution_tier if flight_number else None,
            "missing_reason": None if flight_number else MissingReason.NOT_PRESENT_IN_DOM.value,
        },
        "fare_family": {
            "status": FieldStatus.UNAVAILABLE.value,
            "source": None,
            "missing_reason": MissingReason.NOT_PRESENT_IN_DOM.value,
        },
    }

    return {
        "source": source_id,
        "display_source": "google_flights",
        "booking_source": None,
        "source_url": source_url,
        "origin": request.origin,
        "destination": request.destination,
        "travel_date": request.travel_date.isoformat(),
        "airline": airline,
        "flight_number": flight_number,
        "departure_time_local": departure_time_local,
        "arrival_time_local": arrival_time_local,
        "stops": stops,
        # Strictly unbundled components are None (Phase 10 & 20)
        "base_fare": None,
        "taxes": None,
        "fees": None,
        "gst": None,
        "airport_charges": None,
        "security_fee": None,
        "convenience_fee": None,
        "discount": None,
        "total_fare": total_fare_val,
        "currency": "INR",
        "price_status": price_status,
        "price_raw_text": price_raw,
        "availability": "AVAILABLE",
        "cabin": request.cabin.value if hasattr(request.cabin, 'value') else request.cabin,
        "passenger_count": request.passenger_count.adults + request.passenger_count.children + request.passenger_count.infants,
        "trip_type": request.trip_type.value if hasattr(request.trip_type, 'value') else request.trip_type,
        "collection_run_id": str(run_id) if run_id else None,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "lead_days": request.lead_days,
        "adapter_version": "1.0.0",
        "normalizer_version": "1.0.0",
        # Google result category & rank metadata (Phase 7)
        "google_result_category": category,
        "google_result_rank": rank,
        "field_provenance": field_provenance,
    }
