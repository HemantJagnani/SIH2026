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
    
    # 1. Try modern live Angular layout (.fltResult)
    flt_cards = soup.select(".fltResult")
    if flt_cards:
        logger.info(f"EaseMyTripParser: Found {len(flt_cards)} live cards matching .fltResult")
        from datetime import timedelta
        airline_map = {
            "6E": "IndiGo",
            "AI": "Air India",
            "IX": "Air India Express",
            "SG": "SpiceJet",
            "QP": "AkasaAir",
            "UK": "Vistara",
            "I5": "AirAsia India",
        }
        for card in flt_cards:
            try:
                aircode = card.get("aircode", "").strip()
                airline = airline_map.get(aircode, aircode or "UNKNOWN")
                fn = card.get("fn", "").strip()
                flight_num = f"{aircode}-{fn}" if aircode and fn else fn or "UNKNOWN"
                
                price_str = card.get("price", "").replace(",", "").strip()
                if not price_str:
                    continue
                try:
                    total_fare = float(price_str)
                except ValueError:
                    continue
                
                dep_str = card.get("deptm", "").strip()
                arr_str = card.get("arrtm", "").strip()
                
                dep_dt_local = None
                arr_dt_local = None
                if dep_str and ":" in dep_str:
                    dh, dm = map(int, dep_str.split(":")[:2])
                    dep_dt_local = datetime.combine(request.travel_date, datetime.min.time()).replace(
                        hour=dh, minute=dm, tzinfo=timezone.utc
                    )
                if arr_str and ":" in arr_str:
                    ah, am = map(int, arr_str.split(":")[:2])
                    arr_dt_local = datetime.combine(request.travel_date, datetime.min.time()).replace(
                        hour=ah, minute=am, tzinfo=timezone.utc
                    )
                    if dep_dt_local and arr_dt_local < dep_dt_local:
                        arr_dt_local += timedelta(days=1)
                
                stop_str = card.get("stop", "").strip()
                stops = int(stop_str) if stop_str.isdigit() else None
                
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
                    airline_code=aircode or None,
                    flight_number=flight_num,
                    departure_time_local=dep_dt_local,
                    arrival_time_local=arr_dt_local,
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
                logger.warning(f"EaseMyTripParser: Error parsing live card: {e}")
                
        logger.info(f"EaseMyTripParser: Found {len(observations)} observations in live DOM.")
        return observations

    # 2. Fall back to offline/fixture layout (.nw_listing_bx)
    cards = soup.select(".nw_listing_bx")
    
    if not cards:
        logger.warning("EaseMyTripParser: No flight cards found in DOM using .fltResult or .nw_listing_bx.")
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
                
            # Timing extraction from .tm_lc
            dep_time_el = card.select_one(".tm_lc.texrgt h4")
            arr_time_el = card.select_one(".tm_lc:not(.texrgt) h4")
            
            dep_dt_local = None
            arr_dt_local = None
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
                        
            if arr_time_el:
                arr_str = arr_time_el.get_text(strip=True)
                if ":" in arr_str:
                    try:
                        ah, am = map(int, arr_str.split(":")[:2])
                        arr_dt_local = datetime.combine(request.travel_date, datetime.min.time()).replace(
                            hour=ah, minute=am, tzinfo=timezone.utc
                        )
                        # If arrival time is earlier than departure time, flight arrives next day
                        if dep_dt_local and arr_dt_local < dep_dt_local:
                            from datetime import timedelta
                            arr_dt_local += timedelta(days=1)
                    except Exception:
                        pass

            # Stops and duration from .tmln_rc (could be "05h 20m 1 Stop" or "Non Stop")
            stops = None
            duration_minutes = None
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
                        
                # Extract duration e.g. "02h 15m" or "5h 20m"
                import re
                dur_match = re.search(r'(?:(\d+)\s*h)?\s*(?:(\d+)\s*m)?', dur_text)
                if dur_match:
                    hours = int(dur_match.group(1)) if dur_match.group(1) else 0
                    mins = int(dur_match.group(2)) if dur_match.group(2) else 0
                    if hours > 0 or mins > 0:
                        duration_minutes = hours * 60 + mins
                        
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
                departure_time_local=dep_dt_local,
                arrival_time_local=arr_dt_local,
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
