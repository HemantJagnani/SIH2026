import logging
from typing import List
from uuid import UUID

from models.observation import FareObservation
from models.request import FareSearchRequest
from models.enums import AvailabilityStatus

logger = logging.getLogger(__name__)

def parse_network_response(response_data: dict, request: FareSearchRequest, run_id: UUID, source_id: str) -> List[FareObservation]:
    """Parse JSON network response into canonical fare observations."""
    logger.info("EaseMyTripParser: Parsing network response...")
    observations = []
    # Implementation for structured parsing would go here
    return observations

def parse_dom(html: str, request: FareSearchRequest, run_id: UUID, source_id: str) -> List[FareObservation]:
    """Parse HTML DOM into canonical fare observations."""
    logger.info("EaseMyTripParser: Parsing DOM...")
    observations = []
    
    from bs4 import BeautifulSoup
    from datetime import datetime, timezone
    
    soup = BeautifulSoup(html, "html.parser")
    
    # 1. Extract the 145 main flight cards through .nw_listing_bx
    cards = soup.select(".nw_listing_bx")
    
    if not cards:
        logger.warning("EaseMyTripParser: No flight cards found in DOM using .nw_listing_bx.")
        return observations
        
    for card in cards:
        try:
            # 2. Airline from .air_nmm_txt h6
            airline_el = card.select_one(".air_nmm_txt h6")
            airline = airline_el.get_text(strip=True) if airline_el else "UNKNOWN"
            
            # 3. Flight number from .air_nmm_txt span
            flight_num_el = card.select_one(".air_nmm_txt span")
            flight_num = flight_num_el.get_text(strip=True) if flight_num_el else "UNKNOWN"
            
            # 4. Primary observed fare from h4[id^="spnPrice"]
            price_el = card.select_one("h4[id^='spnPrice']")
            if not price_el:
                continue
            
            price_str = price_el.get_text(strip=True).replace(",", "").replace("₹", "").replace("Rs", "").strip()
            try:
                total_fare = float(price_str)
            except ValueError:
                continue
                
            # Stops from .tmln_rc (could be "Non Stop" or "1 Stop")
            stops = None
            duration_el = card.select_one(".tmln_rc")
            if duration_el:
                dur_text = duration_el.get_text(strip=True).lower()
                if "non stop" in dur_text or "non-stop" in dur_text:
                    stops = 0
                elif "stop" in dur_text:
                    import re
                    match = re.search(r'(\d+)\s*stop', dur_text)
                    if match:
                        stops = int(match.group(1))
                        
            # Note: We do not treat Lock Price, seat count, discount text, or More Fare modal prices as primary fare.
            # Preserve unknown base/tax/fee components as null (they are absent in FareObservation creation, default to None)
            
            obs = FareObservation(
                collection_run_id=run_id,
                source=source_id,
                origin=request.origin,
                destination=request.destination,
                travel_date=request.travel_date,
                lead_days=request.lead_days,
                collected_at=datetime.now(timezone.utc),
                search_timestamp=datetime.now(timezone.utc),
                airline=airline,
                flight_number=flight_num,
                trip_type=request.trip_type,
                cabin=request.cabin,
                passenger_count=1,
                stops=stops,
                source_offer_id=f"emt-{flight_num}-{int(total_fare)}",
                availability=AvailabilityStatus.AVAILABLE,
                adapter_version="1.0.0",
                normalizer_version="1.0.0",
                total_fare=total_fare,
                currency="INR"
            )
            observations.append(obs)
        except Exception as e:
            logger.warning(f"EaseMyTripParser: Error parsing card: {e}")
            
    logger.info(f"EaseMyTripParser: Found {len(observations)} observations in DOM.")
    return observations
