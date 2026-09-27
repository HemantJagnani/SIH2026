"""
DOM and Network Parser for EaseMyTrip.

Enforces:
- Phase 14: Validated selectors, strict card completeness validation.
- Phase 15: Support for multiple fare options (1 Itinerary -> Many Offers).
- Phase 20: No fabricated taxes, fees, or baggage.
- Phase 3: Field provenance.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, List, Optional
from uuid import UUID
from bs4 import BeautifulSoup, Tag

from models.enums import AvailabilityStatus, CabinClass, TripType
from models.observation import FareObservation
from models.provenance import FieldStatus, MissingReason
from models.request import FareSearchRequest
from sources.easemytrip.fare_options import extract_fare_options_from_card

logger = logging.getLogger(__name__)


def parse_network_response(
    response_data: dict,
    request: FareSearchRequest,
    run_id: UUID,
    source_id: str,
) -> List[FareObservation]:
    """Parse JSON network response into canonical fare observations if available."""
    logger.info("EaseMyTripParser: Parsing network response...")
    observations: List[FareObservation] = []
    return observations


def parse_dom(
    html: str,
    request: FareSearchRequest,
    run_id: UUID,
    source_id: str,
    include_fare_options: bool = False,
    source_url: Optional[str] = None,
) -> List[FareObservation]:
    """
    Parse HTML DOM into canonical fare observations.
    
    If include_fare_options is True:
        Extracts each distinct fare offer (Value, EMTEXCLUSIVE, Classic, Flex) as a separate observation.
    If include_fare_options is False:
        Extracts the primary displayed fare observation per card (preserving 1 observation per card).
    """
    logger.info("EaseMyTripParser: Parsing DOM...")
    observations: List[FareObservation] = []

    if not html:
        return observations

    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")
    cards = soup.select(".nw_listing_bx")

    if not cards:
        logger.warning("EaseMyTripParser: No flight cards found in DOM using .nw_listing_bx.")
        return observations

    for card in cards:
        try:
            # 1. Airline (.air_nmm_txt h6)
            airline_el = card.select_one(".air_nmm_txt h6")
            airline = airline_el.get_text(strip=True) if airline_el else None

            # 2. Flight number (.air_nmm_txt span)
            flight_num_el = card.select_one(".air_nmm_txt span")
            flight_num = flight_num_el.get_text(strip=True) if flight_num_el else None

            # 3. Departure time (.tm_lc.texrgt h4)
            dep_time_el = card.select_one(".tm_lc.texrgt h4")
            dep_dt_local = None
            if dep_time_el:
                dep_str = dep_time_el.get_text(strip=True)
                if ":" in dep_str:
                    try:
                        dh, dm = map(int, dep_str.split(":")[:2])
                        dep_dt_local = datetime.combine(request.travel_date, datetime.min.time()).replace(
                            hour=dh, minute=dm, tzinfo=timezone.utc
                        )
                    except Exception:
                        pass

            # 4. Arrival time (.tm_lc:not(.texrgt) h4)
            arr_time_el = card.select_one(".tm_lc:not(.texrgt) h4")
            arr_dt_local = None
            if arr_time_el:
                arr_str = arr_time_el.get_text(strip=True)
                if ":" in arr_str:
                    try:
                        ah, am = map(int, arr_str.split(":")[:2])
                        arr_dt_local = datetime.combine(request.travel_date, datetime.min.time()).replace(
                            hour=ah, minute=am, tzinfo=timezone.utc
                        )
                        if dep_dt_local and arr_dt_local < dep_dt_local:
                            arr_dt_local += timedelta(days=1)
                    except Exception:
                        pass

            # 5. Primary observed fare from h4[id^="spnPrice"]
            price_el = card.select_one("h4[id^='spnPrice']")
            total_fare = None
            price_raw = None
            if price_el:
                price_raw = price_el.get_text(strip=True)
                price_str = price_raw.replace(",", "").replace("₹", "").replace("Rs", "").strip()
                try:
                    total_fare = float(price_str)
                except ValueError:
                    pass

            # --- Phase 14 Card Completeness Validation ---
            # Must have: airline, route, departure, arrival, price
            if not airline or airline == "UNKNOWN":
                logger.debug("EaseMyTripParser: Rejected card with missing airline.")
                continue
            if not request.origin or not request.destination:
                continue
            if dep_dt_local is None or arr_dt_local is None:
                logger.debug("EaseMyTripParser: Rejected card with unparseable departure/arrival times.")
                continue
            if total_fare is None or total_fare <= 0:
                logger.debug("EaseMyTripParser: Rejected card with invalid/missing price.")
                continue

            # Stops and duration from .tmln_rc
            stops = 0
            duration_el = card.select_one(".tmln_rc")
            if duration_el:
                dur_text = duration_el.get_text(strip=True).lower()
                if "non stop" in dur_text or "non-stop" in dur_text:
                    stops = 0
                elif "stop" in dur_text:
                    match = re.search(r'(\d+)\s*stop', dur_text)
                    if match:
                        stops = int(match.group(1))

            # Helper to create observation
            def build_obs(
                fare_val: float,
                raw_prc_txt: str,
                family: Optional[str] = None,
                cabin_kg: Optional[int] = None,
                checkin_kg: Optional[int] = None,
                cancel_fee: Optional[Decimal] = None,
                chg_fee: Optional[Decimal] = None,
                ref_status: Optional[str] = None,
            ) -> FareObservation:
                prov: dict[str, Any] = {
                    "total_fare": {
                        "status": FieldStatus.OBSERVED.value,
                        "source": "EASEMYTRIP_DOM",
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
                    "flight_number": {
                        "status": FieldStatus.OBSERVED.value if flight_num else FieldStatus.UNAVAILABLE.value,
                        "source": "EASEMYTRIP_DOM" if flight_num else None,
                        "missing_reason": None if flight_num else MissingReason.NOT_PRESENT_IN_DOM.value,
                    },
                    "fare_family": {
                        "status": FieldStatus.OBSERVED.value if family else FieldStatus.UNAVAILABLE.value,
                        "source": "EASEMYTRIP_DOM" if family else None,
                        "missing_reason": None if family else MissingReason.NOT_PRESENT_IN_DOM.value,
                    },
                    "cabin_baggage_kg": {
                        "status": FieldStatus.OBSERVED.value if cabin_kg is not None else FieldStatus.UNAVAILABLE.value,
                        "source": "EASEMYTRIP_DOM" if cabin_kg is not None else None,
                        "missing_reason": None if cabin_kg is not None else MissingReason.NOT_PRESENT_IN_DOM.value,
                    },
                    "checkin_baggage_kg": {
                        "status": FieldStatus.OBSERVED.value if checkin_kg is not None else FieldStatus.UNAVAILABLE.value,
                        "source": "EASEMYTRIP_DOM" if checkin_kg is not None else None,
                        "missing_reason": None if checkin_kg is not None else MissingReason.NOT_PRESENT_IN_DOM.value,
                    },
                    "cancellation_fee": {
                        "status": FieldStatus.OBSERVED.value if cancel_fee is not None else FieldStatus.UNAVAILABLE.value,
                        "source": "EASEMYTRIP_DOM" if cancel_fee is not None else None,
                        "missing_reason": None if cancel_fee is not None else MissingReason.NOT_PRESENT_IN_DOM.value,
                    },
                    "change_fee": {
                        "status": FieldStatus.OBSERVED.value if chg_fee is not None else FieldStatus.UNAVAILABLE.value,
                        "source": "EASEMYTRIP_DOM" if chg_fee is not None else None,
                        "missing_reason": None if chg_fee is not None else MissingReason.NOT_PRESENT_IN_DOM.value,
                    },
                    "refund_status": {
                        "status": FieldStatus.OBSERVED.value if ref_status is not None else FieldStatus.UNAVAILABLE.value,
                        "source": "EASEMYTRIP_DOM" if ref_status is not None else None,
                        "missing_reason": None if ref_status is not None else MissingReason.NOT_PRESENT_IN_DOM.value,
                    },
                }

                offer_suffix = f"-{family}" if family else ""
                return FareObservation(
                    collection_run_id=run_id,
                    source=source_id,
                    source_url=source_url,
                    origin=request.origin,
                    destination=request.destination,
                    travel_date=request.travel_date,
                    lead_days=request.lead_days,
                    collected_at=datetime.now(timezone.utc),
                    search_timestamp=datetime.now(timezone.utc),
                    airline=airline,
                    flight_number=flight_num,
                    departure_time_local=dep_dt_local,
                    arrival_time_local=arr_dt_local,
                    trip_type=request.trip_type,
                    cabin=request.cabin,
                    passenger_count=1,
                    stops=stops,
                    fare_family=family,
                    base_fare=None,
                    taxes=None,
                    fees=None,
                    gst=None,
                    airport_charges=None,
                    convenience_fee=None,
                    discount=None,
                    cabin_baggage_kg=cabin_kg,
                    checkin_baggage_kg=checkin_kg,
                    cancellation_fee=cancel_fee,
                    change_fee=chg_fee,
                    refund_status=ref_status,
                    total_fare=fare_val,
                    currency="INR",
                    price_raw_text=raw_prc_txt,
                    price_status="DISPLAYED_TOTAL",
                    source_offer_id=f"emt-{flight_num or 'flight'}-{int(fare_val)}{offer_suffix}",
                    availability=AvailabilityStatus.AVAILABLE,
                    adapter_version="1.0.0",
                    normalizer_version="1.0.0",
                    field_provenance=prov,
                )

            # Check if multiple fare offers should be extracted (Phase 15)
            if include_fare_options:
                fare_options = extract_fare_options_from_card(card)
                if fare_options:
                    for opt in fare_options:
                        observations.append(build_obs(
                            fare_val=opt.total_fare,
                            raw_prc_txt=opt.raw_text,
                            family=opt.fare_family,
                            cabin_kg=opt.cabin_baggage_kg,
                            checkin_kg=opt.checkin_baggage_kg,
                            cancel_fee=opt.cancellation_fee,
                            chg_fee=opt.change_fee,
                            ref_status=opt.refund_status,
                        ))
                else:
                    observations.append(build_obs(total_fare, price_raw or f"₹{total_fare}"))
            else:
                observations.append(build_obs(total_fare, price_raw or f"₹{total_fare}"))

        except Exception as e:
            logger.warning(f"EaseMyTripParser: Error parsing card: {e}")

    logger.info(f"EaseMyTripParser: Found {len(observations)} observations in DOM.")
    return observations
