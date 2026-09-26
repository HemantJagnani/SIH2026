"""
FlightNumberResolver for Google Flights.

Follows strict multi-tier resolution order per Phase 8 spec:
1. visible result-card text
2. aria/accessibility attributes
3. structured DOM relationship
4. expanded flight details
5. permitted booking/fare detail metadata
6. unresolved (returns None)

CRITICAL: Never invent flight numbers!
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)

# Known Indian/regional airline codes
AIRLINE_IATA_CODES = {
    "6E", "AI", "UK", "SG", "QP", "I5", "IX", "G8", "S5", "9I", "EK", "QR", "EY", "SQ", "MH", "TG"
}

# Regex pattern for airline flight numbers: e.g. "6E 512", "6E-512", "AI 101", "UK-994", "QP 1302"
FLIGHT_NUM_PATTERN = re.compile(
    r'\b([A-Z0-9]{2})\s*[-]?\s*(\d{2,4})\b',
    re.IGNORECASE
)


class FlightNumberResolution:
    def __init__(self, flight_number: Optional[str], resolution_tier: str):
        self.flight_number = flight_number
        self.resolution_tier = resolution_tier


class FlightNumberResolver:
    """
    Resolves flight number using multi-tier fallback without guessing.
    """

    @classmethod
    def resolve(
        cls,
        card_soup: Tag | BeautifulSoup,
        expanded_soup: Optional[Tag | BeautifulSoup] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> FlightNumberResolution:
        """
        Attempt resolution in the exact prioritized order.
        """
        # Tier 1: Visible result-card text
        flight_no = cls._resolve_from_visible_text(card_soup)
        if flight_no:
            return FlightNumberResolution(flight_no, "VISIBLE_RESULT_CARD_TEXT")

        # Tier 2: ARIA / Accessibility attributes
        flight_no = cls._resolve_from_aria_attributes(card_soup)
        if flight_no:
            return FlightNumberResolution(flight_no, "ARIA_ACCESSIBILITY_ATTRIBUTES")

        # Tier 3: Structured DOM relationships
        flight_no = cls._resolve_from_structured_dom(card_soup)
        if flight_no:
            return FlightNumberResolution(flight_no, "STRUCTURED_DOM_RELATIONSHIP")

        # Tier 4: Expanded flight details
        if expanded_soup:
            flight_no = cls._resolve_from_expanded_details(expanded_soup)
            if flight_no:
                return FlightNumberResolution(flight_no, "EXPANDED_FLIGHT_DETAILS")

        # Tier 5: Permitted booking/fare detail metadata
        if metadata:
            flight_no = cls._resolve_from_metadata(metadata)
            if flight_no:
                return FlightNumberResolution(flight_no, "PERMITTED_METADATA")

        # Tier 6: Unresolved
        logger.debug("FlightNumberResolver: could not resolve flight number; leaving as None.")
        return FlightNumberResolution(None, "UNRESOLVED")

    @classmethod
    def _resolve_from_visible_text(cls, soup: Tag | BeautifulSoup) -> Optional[str]:
        text = soup.get_text(separator=" ", strip=True)
        # Look specifically for patterns prefixed with "Flight" or standard airline codes
        flight_prefix_match = re.search(r'Flight\s+([A-Z0-9]{2}\s*[-]?\s*\d{2,4})', text, re.IGNORECASE)
        if flight_prefix_match:
            return cls._normalize_flight_number(flight_prefix_match.group(1))

        # Check for airline code matches
        for match in FLIGHT_NUM_PATTERN.finditer(text):
            code = match.group(1).upper()
            num = match.group(2)
            if code in AIRLINE_IATA_CODES:
                return f"{code}-{num}"

        return None

    @classmethod
    def _resolve_from_aria_attributes(cls, soup: Tag | BeautifulSoup) -> Optional[str]:
        for el in soup.find_all(True):
            aria_label = el.get("aria-label", "")
            title = el.get("title", "")
            for candidate in (aria_label, title):
                if candidate and ("flight" in candidate.lower() or any(c in candidate.upper() for c in AIRLINE_IATA_CODES)):
                    match = FLIGHT_NUM_PATTERN.search(candidate)
                    if match:
                        code = match.group(1).upper()
                        num = match.group(2)
                        if code in AIRLINE_IATA_CODES or "flight" in candidate.lower():
                            return f"{code}-{num}"
        return None

    @classmethod
    def _resolve_from_structured_dom(cls, soup: Tag | BeautifulSoup) -> Optional[str]:
        # Look for elements with flight data-attributes or classes
        selectors = [
            "[data-flight-number]",
            "[data-flight]",
            "span[class*='flightNumber']",
            "div[class*='flightNumber']",
        ]
        for sel in selectors:
            el = soup.select_one(sel)
            if el:
                val = el.get("data-flight-number") or el.get("data-flight") or el.get_text(strip=True)
                if val:
                    norm = cls._normalize_flight_number(val)
                    if norm:
                        return norm
        return None

    @classmethod
    def _resolve_from_expanded_details(cls, soup: Tag | BeautifulSoup) -> Optional[str]:
        text = soup.get_text(separator=" ", strip=True)
        # Check for "Flight <code/num>" in expanded panel
        match = re.search(r'(?:Flight|Flight number|Flight no\.?)\s*:?\s*([A-Z0-9]{2}\s*[-]?\s*\d{2,4})', text, re.IGNORECASE)
        if match:
            return cls._normalize_flight_number(match.group(1))

        # Check for airline code pattern inside region/details elements
        for match in FLIGHT_NUM_PATTERN.finditer(text):
            code = match.group(1).upper()
            num = match.group(2)
            if code in AIRLINE_IATA_CODES:
                return f"{code}-{num}"
        return None

    @classmethod
    def _resolve_from_metadata(cls, metadata: dict[str, Any]) -> Optional[str]:
        # If url or booking params expose flight number
        for key in ("flight_number", "flight", "fno", "flight_no"):
            if key in metadata and metadata[key]:
                return cls._normalize_flight_number(str(metadata[key]))
        return None

    @classmethod
    def _normalize_flight_number(cls, raw: str) -> Optional[str]:
        raw = raw.strip().upper()
        match = FLIGHT_NUM_PATTERN.search(raw)
        if match:
            code = match.group(1).upper()
            num = match.group(2)
            return f"{code}-{num}"
        return None
