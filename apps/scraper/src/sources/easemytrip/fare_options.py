"""
EaseMyTrip Fare Options Extractor (Phase 15).

Extracts multiple fare offers for a single flight itinerary:
1 Itinerary -> Many Fare Offers (e.g. Value, EMTEXCLUSIVE, Classic, Flex).
Never collapses distinct fare offers into one.
"""

from __future__ import annotations

import logging
import re
from decimal import Decimal
from typing import Any, List, Optional
from uuid import UUID
from bs4 import Tag

from models.itinerary import FareOffer, Itinerary, PriceStatus
from models.provenance import FieldStatus, MissingReason
from models.enums import AvailabilityStatus, CabinClass

logger = logging.getLogger(__name__)


class EaseMyTripFareOption:
    def __init__(
        self,
        fare_family: str,
        total_fare: float,
        raw_text: str,
        cabin_baggage_kg: Optional[int] = None,
        checkin_baggage_kg: Optional[int] = None,
        cancellation_fee: Optional[Decimal] = None,
        change_fee: Optional[Decimal] = None,
        refund_status: Optional[str] = None,
    ):
        self.fare_family = fare_family
        self.total_fare = total_fare
        self.raw_text = raw_text
        self.cabin_baggage_kg = cabin_baggage_kg
        self.checkin_baggage_kg = checkin_baggage_kg
        self.cancellation_fee = cancellation_fee
        self.change_fee = change_fee
        self.refund_status = refund_status


def extract_fare_options_from_card(card: Tag) -> List[EaseMyTripFareOption]:
    """
    Extracts all exposed fare offers from an EaseMyTrip flight card (.nw_listing_bx).
    Identifies labels with .fareheader and .fareprice (e.g. Value, EMTEXCLUSIVE, Classic, Flex).
    Captures explicitly displayed baggage kg and cancellation/change fees if present.
    Never invents unexposed fields.
    """
    options: List[EaseMyTripFareOption] = []
    seen_combos = set()

    # Look for fare option boxes
    option_boxes = card.select("._mfarebx, label:has(.fareheader), div:has(> .fareheader)")
    for box in option_boxes:
        header_el = box.select_one(".fareheader")
        price_el = box.select_one(".fareprice")

        if header_el and price_el:
            family = header_el.get_text(strip=True)
            price_raw = price_el.get_text(strip=True)

            # Clean price string
            clean_price = price_raw.replace(",", "").replace("₹", "").replace("Rs", "").replace("INR", "").strip()
            try:
                price_val = float(clean_price)
            except ValueError:
                continue

            combo_key = (family.upper(), price_val)
            if combo_key not in seen_combos:
                seen_combos.add(combo_key)
                
                # Extract explicit details from box text if available
                box_text = " ".join(box.stripped_strings)
                cabin_kg: Optional[int] = None
                checkin_kg: Optional[int] = None
                cancel_fee: Optional[Decimal] = None
                chg_fee: Optional[Decimal] = None
                ref_status: Optional[str] = None

                # Cabin baggage: e.g. "7 Kgs Cabin"
                m_cabin = re.search(r'(\d+)\s*Kgs?\s*Cabin', box_text, re.IGNORECASE)
                if m_cabin:
                    cabin_kg = int(m_cabin.group(1))

                # Check-in baggage: e.g. "15 Kgs Check-in" or "20 Kgs Check-in"
                m_checkin = re.search(r'(\d+)\s*Kgs?\s*Check-in', box_text, re.IGNORECASE)
                if m_checkin:
                    checkin_kg = int(m_checkin.group(1))

                # Cancellation fee: e.g. "Cancellation fee starts at ₹ 4,299"
                m_cancel = re.search(r'Cancellation\s*fee\s*starts\s*at\s*[₹Rs\.]*\s*([\d,]+)', box_text, re.IGNORECASE)
                if m_cancel:
                    cancel_fee = Decimal(m_cancel.group(1).replace(",", ""))
                    ref_status = "CONDITIONAL"
                elif "Non-Refundable" in box_text or "Non Refundable" in box_text:
                    ref_status = "NON_REFUNDABLE"
                elif "Refundable" in box_text:
                    ref_status = "REFUNDABLE"

                # Date change fee: e.g. "Date Change fee starts at ₹ 3,499" or "₹ 0"
                m_change = re.search(r'Date\s*Change\s*fee\s*starts\s*at\s*[₹Rs\.]*\s*([\d,]+)', box_text, re.IGNORECASE)
                if m_change:
                    chg_fee = Decimal(m_change.group(1).replace(",", ""))

                options.append(EaseMyTripFareOption(
                    fare_family=family,
                    total_fare=price_val,
                    raw_text=price_raw,
                    cabin_baggage_kg=cabin_kg,
                    checkin_baggage_kg=checkin_kg,
                    cancellation_fee=cancel_fee,
                    change_fee=chg_fee,
                    refund_status=ref_status,
                ))

    return options
