import os
import aiohttp
import json
import logging
from datetime import datetime

from adapters.base import FareSourceAdapter
from adapters.models import CollectionResult, CollectionStatus, FareSearchRequest
from models.enums import AvailabilityStatus
from models.observation import FareObservation

logger = logging.getLogger(__name__)


class IgnavAdapter(FareSourceAdapter):
    """
    Adapter for the Ignav Live API (ignav.com).
    """

    @property
    def adapter_version(self) -> str:
        return "1.0.0"

    @property
    def parser_version(self) -> str:
        return "1.0.0"
        
    def __init__(self):
        self.api_url = "https://ignav.com/api/fares/one-way"
        self.api_key = os.getenv("IGNAV_API_KEY", "")

    async def _fetch(self, request: FareSearchRequest) -> tuple[dict | None, int | None]:
        headers = {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json"
        }
        
        # Build the payload according to Ignav OpenAPI spec
        payload = {
            "origin": request.origin,
            "destination": request.destination,
            "departure_date": request.travel_date.isoformat(),
            "adults": request.adults,
            "children": request.children,
            "infants_in_seat": request.infants,
            "infants_on_lap": 0,
            "cabin_class": request.cabin.name.lower(),
            "market": "IN"
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(self.api_url, json=payload, headers=headers) as response:
                    http_status = response.status
                    if http_status == 200:
                        data = await response.json()
                        return data, http_status
                    elif http_status == 429:
                        logger.error("[IgnavAdapter] Rate limited.")
                        return None, http_status
                    elif http_status in (401, 403):
                        logger.error(f"[IgnavAdapter] Auth error (status {http_status}).")
                        return None, http_status
                    else:
                        text = await response.text()
                        logger.error(f"[IgnavAdapter] Unhandled HTTP {http_status}: {text}")
                        return None, http_status
            except Exception as e:
                logger.error(f"[IgnavAdapter] Request failed: {e}")
                return None, None

    def _parse(self, raw_data: dict, request: FareSearchRequest) -> list[FareObservation]:
        observations = []
        
        # Ignav returns itineraries list
        itineraries = raw_data.get("itineraries", [])
        collected_at = datetime.utcnow()
        
        for idx, itin in enumerate(itineraries):
            try:
                # 1. Prices and Validation
                price_obj = itin.get("price", {})
                currency = price_obj.get("currency", "").upper()
                if currency != "INR":
                    # The user rule states: "quarantine/mark invalid; never silently convert"
                    # For POC, we skip or set availability to an error state. 
                    # Since we require valid INR for this index, let's skip non-INR entirely for now,
                    # or we could insert it and let the validator catch it.
                    # We will construct it and let the normalizer/validator handle rejection, but 
                    # it MUST be marked with the actual currency.
                    pass
                
                amount = price_obj.get("amount")
                price_status = price_obj.get("status")
                ignav_id = itin.get("ignav_id")
                requires_self_transfer = itin.get("requires_self_transfer")
                
                # 2. Segments
                outbound = itin.get("outbound", {})
                segments = outbound.get("segments", [])
                if not segments:
                    continue
                
                stops = max(len(segments) - 1, 0)
                first_seg = segments[0]
                last_seg = segments[-1]
                
                airline_code = first_seg.get("marketing_carrier_code")
                airline = first_seg.get("operating_carrier_name") or airline_code or "Unknown"
                flight_number = first_seg.get("flight_number")
                
                # Formatting flight number as "CODE NUM"
                if flight_number and airline_code and not flight_number.startswith(airline_code):
                    full_flight_number = f"{airline_code} {flight_number}"
                else:
                    full_flight_number = flight_number
                    
                # 3. Times
                def parse_time(ts_str):
                    if not ts_str:
                        return None
                    # Ignav returns ISO strings like 2026-10-08T10:00:00
                    try:
                        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    except ValueError:
                        return None

                departure_time_local = parse_time(first_seg.get("departure_time_local"))
                departure_time_utc = parse_time(first_seg.get("departure_time_utc"))
                arrival_time_local = parse_time(last_seg.get("arrival_time_local"))
                arrival_time_utc = parse_time(last_seg.get("arrival_time_utc"))
                
                cabin_str = itin.get("cabin_class", request.cabin.name)
                
                # 4. Construct Observation
                obs = FareObservation(
                    collection_run_id=request.request_id,
                    source="ignav",
                    source_itinerary_id=ignav_id,
                    collected_at=collected_at,
                    travel_date=request.travel_date,
                    lead_days=request.lead_days,
                    origin=request.origin,
                    destination=request.destination,
                    airline=airline,
                    airline_code=airline_code,
                    flight_number=full_flight_number,
                    trip_type=request.trip_type,
                    cabin=request.cabin, # Mapping logic for cabin could be added
                    passenger_count=request.adults + request.children + request.infants,
                    departure_time_local=departure_time_local,
                    departure_time_utc=departure_time_utc,
                    arrival_time_local=arrival_time_local,
                    arrival_time_utc=arrival_time_utc,
                    stops=stops,
                    total_fare=amount,
                    currency=currency,
                    price_status=price_status,
                    requires_self_transfer=requires_self_transfer,
                    availability=AvailabilityStatus.AVAILABLE,
                    adapter_version=self.adapter_version,
                    normalizer_version="1.0.0"
                )
                observations.append(obs)
            except Exception as e:
                logger.error(f"[IgnavAdapter] Error parsing itinerary {idx}: {e}")
                
        return observations
