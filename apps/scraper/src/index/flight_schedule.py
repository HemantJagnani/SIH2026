"""
DGCA Calendar Year 2024 Approved Domestic Flight Schedule Validation for APIx.

Source Authority:
- Directorate General of Civil Aviation (DGCA), Ministry of Civil Aviation, Government of India.
- Seasonal Operating Approvals:
  * Northern Summer Schedule 2024: Effective March 31, 2024 – October 26, 2024 (24,275 weekly departures, 125 airports).
  * Northern Winter Schedule 2024: Effective October 27, 2024 – March 29, 2025 (25,007 weekly departures, 124 airports).

Methodological Role:
- Flight-Universe Control & Denominator Validation.
- Defines the expected commercial flight universe on travel date d.
- Evaluates scraper coverage: C_scraper = observed_active_flights / DGCA_approved_active_flights.
- Partitions observations into:
  1. OBSERVED_AND_SCHEDULED
  2. SCHEDULED_BUT_NOT_OBSERVED
  3. UNSCHEDULED_OBSERVED
- Validates scraper departure times against official DGCA approved departure-time bands.

STRICT INVARIANTS:
1. Station Disambiguation:
   - South Goa Dabolim (GOI / DABOLIM) and North Goa Manohar International Mopa (GOX / MOPA)
     are distinct commercial stations and must NEVER be merged.
   - Delhi IGI (DEL) and Hindon (HDO) are distinct airports and must NEVER be merged.
2. Anti-Contamination:
   - Flight schedules are a flight-universe/control dataset, NOT a fare-weight or passenger-volume dataset.
   - Schedules must NEVER be used to calculate route weights, lead-time weights, or CPI weights.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

from pydantic import BaseModel, Field

from models.canonical import classify_departure_time_band

logger = logging.getLogger(__name__)

# Constants
DATASET_ID = "DGCA_DOMESTIC_SCHEDULE_CY2024"
SOURCE_AUTHORITY = "Directorate General of Civil Aviation, Ministry of Civil Aviation, Government of India"
REFERENCE_YEAR = 2024
METHODOLOGICAL_ROLE = "REGULATORY_FLIGHT_UNIVERSE_CONTROL"

SUMMER_2024_START = date(2024, 3, 31)
SUMMER_2024_END = date(2024, 10, 26)
WINTER_2024_START = date(2024, 10, 27)
WINTER_2024_END = date(2025, 3, 29)

# Prohibited keys to guard against using schedule IDs as fare or route weights
PROHIBITED_SCHEDULE_WEIGHT_PREFIXES = (
    "DGCA-S24",
    "DGCA-W24",
    "SCHED-",
    "SCHEDULE",
    "DGCA_SCHEDULE",
)


class AmbiguousStationError(ValueError):
    """Raised when an airport station cannot be disambiguated (e.g. unadorned 'GOA')."""
    pass


class ScheduleContaminationError(ValueError):
    """Raised when schedule universe records are improperly passed into pricing or weighting routines."""
    pass


class FlightUniverseStatus(str, Enum):
    """Classification of flight observation against approved regulatory schedule."""
    OBSERVED_AND_SCHEDULED = "OBSERVED_AND_SCHEDULED"
    SCHEDULED_BUT_NOT_OBSERVED = "SCHEDULED_BUT_NOT_OBSERVED"
    UNSCHEDULED_OBSERVED = "UNSCHEDULED_OBSERVED"


# Standard City to IATA Code Mappings
# Strictly keeping GOI (Dabolim) and GOX (Mopa) separate!
# Strictly keeping DEL (IGI) and HDO (Hindon) separate!
CITY_TO_IATA_MAP: Dict[str, str] = {
    # Capital & Metros
    "DELHI": "DEL",
    "NEW DELHI": "DEL",
    "INDIRA GANDHI": "DEL",
    "DEL": "DEL",
    
    "HINDON": "HDO",
    "GHAZIABAD": "HDO",
    "HDO": "HDO",

    "MUMBAI": "BOM",
    "BOMBAY": "BOM",
    "CHHATRAPATI SHIVAJI": "BOM",
    "BOM": "BOM",

    "BENGALURU": "BLR",
    "BANGALORE": "BLR",
    "KEMPEGOWDA": "BLR",
    "BLR": "BLR",

    "KOLKATA": "CCU",
    "CALCUTTA": "CCU",
    "CCU": "CCU",

    "HYDERABAD": "HYD",
    "HYD": "HYD",

    "CHENNAI": "MAA",
    "MADRAS": "MAA",
    "MAA": "MAA",

    # Goa Distinct Stations
    "DABOLIM": "GOI",
    "GOA (DABOLIM)": "GOI",
    "GOA DABOLIM": "GOI",
    "SOUTH GOA": "GOI",
    "GOI": "GOI",

    "MOPA": "GOX",
    "GOA (MOPA)": "GOX",
    "GOA MOPA": "GOX",
    "MANOHAR": "GOX",
    "MANOHAR INTERNATIONAL": "GOX",
    "NORTH GOA": "GOX",
    "GOX": "GOX",

    # Key Tier-1/Tier-2 Stations
    "AHMEDABAD": "AMD",
    "AMD": "AMD",
    "PUNE": "PNQ",
    "PNQ": "PNQ",
    "JAIPUR": "JAI",
    "JAI": "JAI",
    "KOCHI": "COK",
    "COCHIN": "COK",
    "COK": "COK",
    "GUWAHATI": "GAU",
    "GAU": "GAU",
    "LUCKNOW": "LKO",
    "LKO": "LKO",
    "PATNA": "PAT",
    "PAT": "PAT",
    "SRINAGAR": "SXR",
    "SXR": "SXR",
    "VARANASI": "VNS",
    "VNS": "VNS",
    "INDORE": "IDR",
    "IDR": "IDR",
    "CHANDIGARH": "IXC",
    "IXC": "IXC",
    "AMRITSAR": "ATQ",
    "ATQ": "ATQ",
    "BHUBANESWAR": "BBI",
    "BBI": "BBI",
    "BAGDOGRA": "IXB",
    "IXB": "IXB",
    "COIMBATORE": "CJB",
    "CJB": "CJB",
    "TRIVANDRUM": "TRV",
    "THIRUVANANTHAPURAM": "TRV",
    "TRV": "TRV",
    "VISAKHAPATNAM": "VTZ",
    "VTZ": "VTZ",
    "RAIPUR": "RPR",
    "RPR": "RPR",
    "RANCHI": "IXR",
    "IXR": "IXR",
    "LEH": "IXL",
    "IXL": "IXL",
    "AGARTALA": "IXA",
    "IXA": "IXA",
    "NAGPUR": "NAG",
    "NAG": "NAG",
    "TIRUPATI": "TIR",
    "TIR": "TIR",
}

# Airline Normalization Mappings
AIRLINE_CODE_MAP: Dict[str, str] = {
    "6E": "6E",
    "INDIGO": "6E",
    "AI": "AI",
    "AIR INDIA": "AI",
    "UK": "UK",
    "VISTARA": "UK",
    "QP": "QP",
    "AKASA": "QP",
    "AKASA AIR": "QP",
    "SG": "SG",
    "SPICEJET": "SG",
    "IX": "IX",
    "AIR INDIA EXPRESS": "IX",
    "AIX": "IX",
    "9I": "9I",
    "ALLIANCE AIR": "9I",
    "ALLIANCE": "9I",
}


def normalize_station(station: str) -> str:
    """
    Normalizes airport station names or city names to 3-letter IATA codes.
    
    STRICT INVARIANTS:
    - DABOLIM / GOA (DABOLIM) -> GOI
    - MOPA / GOA (MOPA) -> GOX
    - Unadorned 'GOA' raises AmbiguousStationError because Dabolim and Mopa
      must never be merged.
    - DELHI / NEW DELHI -> DEL
    - HINDON / GHAZIABAD -> HDO (Hindon and Delhi IGI are distinct and never merged).
    """
    if not station or not isinstance(station, str):
        raise ValueError("Station name must be a non-empty string")
    
    clean = station.strip().upper()
    
    # Check for ambiguous Goa
    if clean == "GOA":
        raise AmbiguousStationError(
            "Ambiguous station 'GOA': Dabolim (GOI) and Mopa (GOX) are distinct "
            "commercial airports and must be explicitly specified."
        )
    
    if clean in CITY_TO_IATA_MAP:
        return CITY_TO_IATA_MAP[clean]
    
    # If already a valid 3-letter uppercase alphabetic code
    if len(clean) == 3 and clean.isalpha():
        return clean
    
    raise ValueError(f"Unrecognized airport or city name for normalization: '{station}'")


def normalize_airline_code(airline: str) -> str:
    """Normalizes airline name or IATA prefix to standard 2-character code."""
    if not airline or not isinstance(airline, str):
        return "UNKNOWN"
    clean = airline.strip().upper()
    return AIRLINE_CODE_MAP.get(clean, clean[:2] if len(clean) >= 2 else clean)


def parse_frequency(frequency: Union[str, int, Sequence[int]]) -> Set[int]:
    """
    Parses operating frequency into a set of ISO weekday digits:
    1 = Monday, 2 = Tuesday, 3 = Wednesday, 4 = Thursday,
    5 = Friday, 6 = Saturday, 7 = Sunday.
    
    Supports:
    - '1234567' or 'DAILY' -> {1, 2, 3, 4, 5, 6, 7}
    - '135' -> {1, 3, 5} (Mon, Wed, Fri)
    - '67' -> {6, 7} (Sat, Sun)
    - '1-5' -> {1, 2, 3, 4, 5}
    - '1,3,5' -> {1, 3, 5}
    - 1234567 (int) -> {1, 2, 3, 4, 5, 6, 7}
    """
    if frequency is None:
        return set()
    
    if isinstance(frequency, int):
        frequency = str(frequency)
    
    if isinstance(frequency, (list, tuple, set)):
        res = set()
        for x in frequency:
            try:
                ix = int(x)
                if 1 <= ix <= 7:
                    res.add(ix)
            except (ValueError, TypeError):
                continue
        return res
    
    s = str(frequency).strip().upper()
    if s in ("DAILY", "1-7", "1 - 7"):
        return {1, 2, 3, 4, 5, 6, 7}
    if s in ("WEEKDAYS", "1-5", "1 - 5"):
        return {1, 2, 3, 4, 5}
    if s in ("WEEKENDS", "67", "6-7"):
        return {6, 7}
    
    # Handle range syntax like '1-5' or comma-separated '1, 2, 3'
    if "-" in s and len(s) <= 5:
        parts = s.split("-")
        if len(parts) == 2 and parts[0].strip().isdigit() and parts[1].strip().isdigit():
            start, end = int(parts[0].strip()), int(parts[1].strip())
            if 1 <= start <= end <= 7:
                return set(range(start, end + 1))
    
    # Extract all digits 1-7
    digits = set()
    for char in s:
        if char.isdigit():
            val = int(char)
            if 1 <= val <= 7:
                digits.add(val)
    return digits


def normalize_flight_number(raw_flight_no: str, airline_hint: Optional[str] = None) -> Tuple[str, str]:
    """
    Normalizes a flight number string into (airline_code, numeric_or_suffix_part).
    E.g.:
    - '6E 2045'  -> ('6E', '2045')
    - '6E-2045'  -> ('6E', '2045')
    - '6E2045'   -> ('6E', '2045')
    - 'AI 887'   -> ('AI', '887')
    - '2045' with airline_hint='IndiGo' -> ('6E', '2045')
    """
    if not raw_flight_no:
        airline_code = normalize_airline_code(airline_hint) if airline_hint else "UNKNOWN"
        return airline_code, ""
    
    clean = str(raw_flight_no).strip().upper().replace(" ", "").replace("-", "")
    
    # Pure numeric (e.g. '2045')
    if clean.isdigit():
        op = normalize_airline_code(airline_hint) if airline_hint else "UNKNOWN"
        return op, clean

    # Match 2-char airline code (letters or letter+digit, e.g. 6E, AI, 9I, UK, QP) followed by flight number
    match = re.match(r"^([A-Z]{2}|[A-Z][0-9]|[0-9][A-Z])(\d+[A-Z]?)$", clean)
    if match:
        op = normalize_airline_code(match.group(1))
        flt = match.group(2)
        return op, flt
    
    # Fallback
    op = normalize_airline_code(airline_hint) if airline_hint else "UNKNOWN"
    return op, clean


class DGCAScheduledFlight(BaseModel):
    """Single approved flight entry from the DGCA seasonal schedule."""
    schedule_id: str = Field(..., description="Unique schedule record ID")
    season: str = Field(..., description="Schedule season (SUMMER_2024 or WINTER_2024)")
    operator_code: str = Field(..., description="Airline 2-letter code")
    airline: str = Field(..., description="Airline full name")
    flight_no: str = Field(..., description="Official flight number")
    aircraft_type: Optional[str] = Field(default=None, description="Aircraft equipment code")
    origin_city: str = Field(..., description="Origin city name")
    destination_city: str = Field(..., description="Destination city name")
    origin_code: str = Field(..., description="Normalized IATA code of origin")
    destination_code: str = Field(..., description="Normalized IATA code of destination")
    route_id: str = Field(..., description="Canonical route ID e.g. DEL-BOM")
    departure_time: str = Field(..., description="Scheduled departure time HH:MM")
    arrival_time: str = Field(..., description="Scheduled arrival time HH:MM")
    frequency: str = Field(..., description="Raw operating frequency string")
    effective_from: date = Field(..., description="Start date of validity")
    effective_to: date = Field(..., description="End date of validity")
    regulatory_status: str = Field(default="APPROVED")
    note: Optional[str] = None
    operating_days: Set[int] = Field(default_factory=set)
    departure_time_band: str = Field(default="")

    def model_post_init(self, __context: Any) -> None:
        if not self.operating_days:
            self.operating_days = parse_frequency(self.frequency)
        if not self.departure_time_band:
            self.departure_time_band = classify_departure_time_band(self.departure_time)


class MatchedFlightResult(BaseModel):
    """Result of comparing a single flight against the DGCA approved schedule."""
    status: FlightUniverseStatus
    route_id: str
    scheduled_flight: Optional[DGCAScheduledFlight] = None
    observed_flight_number: Optional[str] = None
    observed_airline: Optional[str] = None
    observed_departure_time: Optional[str] = None
    scheduled_departure_time: Optional[str] = None
    scheduled_time_band: Optional[str] = None
    observed_time_band: Optional[str] = None
    band_matches: Optional[bool] = None


class ScraperCoverageReport(BaseModel):
    """
    Summary report comparing observed scraped flights against DGCA approved active flights.
    Provides the core quality metric:
    coverage_metric = observed_active_flights / DGCA_approved_active_flights
    """
    route_id: str
    travel_date: date
    dgca_approved_active_flights: int = Field(..., ge=0, description="Denominator: Active approved flights")
    observed_active_flights: int = Field(..., ge=0, description="Numerator: Approved flights seen by scraper")
    coverage_metric: float = Field(..., ge=0.0, le=1.0, description="Observed scheduled / Approved scheduled")
    scheduled_and_observed_count: int
    scheduled_but_not_observed_count: int
    unscheduled_observed_count: int
    scheduled_and_observed: List[MatchedFlightResult] = Field(default_factory=list)
    scheduled_but_not_observed: List[DGCAScheduledFlight] = Field(default_factory=list)
    unscheduled_observed: List[MatchedFlightResult] = Field(default_factory=list)
    departure_band_mismatches: List[MatchedFlightResult] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def is_flight_active_on_date(flight: DGCAScheduledFlight, target_date: date) -> bool:
    """
    Determines whether a DGCA approved flight operates on a requested travel date:
    1. target_date must be between flight.effective_from and flight.effective_to (inclusive).
    2. target_date day-of-week (isoweekday: 1=Mon..7=Sun) must be in flight.operating_days.
    """
    if not (flight.effective_from <= target_date <= flight.effective_to):
        return False
    iso_day = target_date.isoweekday()
    return iso_day in flight.operating_days


def assert_no_schedule_weight_contamination(weights: Dict[str, Any]) -> None:
    """
    Guards against accidental injection of flight schedule universe IDs or items
    into route-weight, lead-time weight, or CPI weight configurations.
    """
    for k in weights.keys():
        k_str = str(k).strip()
        for prefix in PROHIBITED_SCHEDULE_WEIGHT_PREFIXES:
            if k_str.startswith(prefix) or prefix in k_str:
                raise ScheduleContaminationError(
                    f"CRITICAL METHODOLOGICAL VIOLATION: Flight schedule identifier '{k}' "
                    "cannot be used as a pricing, route, or expenditure weight! "
                    "Approved schedules serve strictly as a flight-universe control."
                )


class DGCAScheduleRegistry:
    """
    Registry for loading, querying, and validating DGCA approved CY2024 domestic schedules.
    """

    def __init__(self, config_path: Optional[Union[str, Path]] = None) -> None:
        if config_path is None:
            # Default location: config/dgca_cy2024_schedule.json
            config_path = Path(__file__).resolve().parents[4] / "config" / "dgca_cy2024_schedule.json"
        
        self.config_path = Path(config_path)
        self.flights: List[DGCAScheduledFlight] = []
        self._flights_by_route: Dict[str, List[DGCAScheduledFlight]] = {}
        self._flights_by_id: Dict[str, DGCAScheduledFlight] = {}
        self.dataset_metadata: Dict[str, Any] = {}
        
        self._load()

    def _load(self) -> None:
        if not self.config_path.exists():
            raise FileNotFoundError(f"DGCA schedule configuration not found at {self.config_path}")
        
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        self.dataset_metadata = {
            "dataset_id": data.get("dataset_id"),
            "source": data.get("source"),
            "source_authority": data.get("source_authority"),
            "reference_year": data.get("reference_year"),
            "methodological_role": data.get("methodological_role"),
            "seasons": data.get("seasons", {}),
        }

        raw_flights = data.get("flights", [])
        for item in raw_flights:
            orig = normalize_station(item["origin_code"] if "origin_code" in item else item["origin_city"])
            dest = normalize_station(item["destination_code"] if "destination_code" in item else item["destination_city"])
            route_id = f"{orig}-{dest}"

            flight = DGCAScheduledFlight(
                schedule_id=item["schedule_id"],
                season=item["season"],
                operator_code=normalize_airline_code(item["operator_code"]),
                airline=item["airline"],
                flight_no=item["flight_no"],
                aircraft_type=item.get("aircraft_type"),
                origin_city=item["origin_city"],
                destination_city=item["destination_city"],
                origin_code=orig,
                destination_code=dest,
                route_id=route_id,
                departure_time=item["departure_time"],
                arrival_time=item["arrival_time"],
                frequency=str(item["frequency"]),
                effective_from=date.fromisoformat(item["effective_from"]),
                effective_to=date.fromisoformat(item["effective_to"]),
                regulatory_status=item.get("regulatory_status", "APPROVED"),
                note=item.get("note"),
            )
            self.flights.append(flight)
            self._flights_by_id[flight.schedule_id] = flight
            self._flights_by_route.setdefault(route_id, []).append(flight)

        logger.info(f"Loaded {len(self.flights)} DGCA CY2024 scheduled flight records across {len(self._flights_by_route)} routes.")

    def get_flights_for_route(self, route_id: str) -> List[DGCAScheduledFlight]:
        """Returns all approved schedule records for a given route (e.g. DEL-BOM)."""
        clean_route = route_id.strip().upper()
        if "-" in clean_route:
            parts = clean_route.split("-")
            clean_route = f"{normalize_station(parts[0])}-{normalize_station(parts[1])}"
        return self._flights_by_route.get(clean_route, [])

    def get_active_flights(self, route_id: str, travel_date: date) -> List[DGCAScheduledFlight]:
        """Returns approved scheduled flights for a route that operate on travel_date."""
        route_flights = self.get_flights_for_route(route_id)
        return [f for f in route_flights if is_flight_active_on_date(f, travel_date)]


# Module-level registry singleton
_GLOBAL_SCHEDULE_REGISTRY: Optional[DGCAScheduleRegistry] = None


def get_schedule_registry(reload: bool = False) -> DGCAScheduleRegistry:
    """Provides singleton access to the DGCA schedule registry."""
    global _GLOBAL_SCHEDULE_REGISTRY
    if _GLOBAL_SCHEDULE_REGISTRY is None or reload:
        _GLOBAL_SCHEDULE_REGISTRY = DGCAScheduleRegistry()
    return _GLOBAL_SCHEDULE_REGISTRY


def evaluate_scraper_coverage(
    scraped_observations: Sequence[Any],
    route_id: str,
    travel_date: date,
    registry: Optional[DGCAScheduleRegistry] = None,
) -> ScraperCoverageReport:
    """
    Evaluates scraper coverage against DGCA approved active domestic flights.
    
    Calculates:
    - coverage_metric = observed_active_flights / DGCA_approved_active_flights
    
    Partitions:
    - OBSERVED_AND_SCHEDULED: in approved schedule and observed by scraper.
    - SCHEDULED_BUT_NOT_OBSERVED: approved for travel_date but missed by scraper.
    - UNSCHEDULED_OBSERVED: observed by scraper but not found in approved schedule.
    
    Validates departure-time bands using DGCA departure time vs observed departure time.
    """
    if registry is None:
        registry = get_schedule_registry()
    
    # Normalize route
    parts = route_id.strip().upper().split("-")
    if len(parts) == 2:
        norm_route = f"{normalize_station(parts[0])}-{normalize_station(parts[1])}"
    else:
        norm_route = route_id.strip().upper()

    # Active DGCA approved flights on travel_date
    approved_active = registry.get_active_flights(norm_route, travel_date)
    approved_by_flight_key: Dict[Tuple[str, str], DGCAScheduledFlight] = {}
    
    for f in approved_active:
        op, num = normalize_flight_number(f.flight_no, f.operator_code)
        approved_by_flight_key[(op, num)] = f

    matched_scheduled_keys: Set[Tuple[str, str]] = set()
    observed_and_scheduled: List[MatchedFlightResult] = []
    unscheduled_observed: List[MatchedFlightResult] = []
    departure_band_mismatches: List[MatchedFlightResult] = []

    for obs in scraped_observations:
        # Extract attributes from FareObservation or dict
        if isinstance(obs, dict):
            obs_airline = obs.get("airline")
            obs_flight_no = obs.get("flight_number") or obs.get("flight_no")
            obs_dep_time = obs.get("departure_time_local") or obs.get("departure_time")
        else:
            obs_airline = getattr(obs, "airline", None)
            obs_flight_no = getattr(obs, "flight_number", None) or getattr(obs, "flight_no", None)
            obs_dep_time = getattr(obs, "departure_time_local", None) or getattr(obs, "departure_time", None)

        obs_op, obs_num = normalize_flight_number(obs_flight_no or "", obs_airline)
        flight_key = (obs_op, obs_num)

        # Classify departure time band for observed flight
        obs_band = classify_departure_time_band(obs_dep_time)

        if flight_key in approved_by_flight_key:
            sched_f = approved_by_flight_key[flight_key]
            matched_scheduled_keys.add(flight_key)
            sched_band = sched_f.departure_time_band
            band_match = (sched_band == obs_band) if obs_band != "UNKNOWN_BAND" else True

            res = MatchedFlightResult(
                status=FlightUniverseStatus.OBSERVED_AND_SCHEDULED,
                route_id=norm_route,
                scheduled_flight=sched_f,
                observed_flight_number=obs_flight_no,
                observed_airline=obs_airline,
                observed_departure_time=str(obs_dep_time) if obs_dep_time else None,
                scheduled_departure_time=sched_f.departure_time,
                scheduled_time_band=sched_band,
                observed_time_band=obs_band,
                band_matches=band_match,
            )
            observed_and_scheduled.append(res)
            if not band_match:
                departure_band_mismatches.append(res)
        else:
            # Not in approved schedule
            res = MatchedFlightResult(
                status=FlightUniverseStatus.UNSCHEDULED_OBSERVED,
                route_id=norm_route,
                scheduled_flight=None,
                observed_flight_number=obs_flight_no,
                observed_airline=obs_airline,
                observed_departure_time=str(obs_dep_time) if obs_dep_time else None,
                scheduled_departure_time=None,
                scheduled_time_band=None,
                observed_time_band=obs_band,
                band_matches=None,
            )
            unscheduled_observed.append(res)

    # Flights in schedule that were NOT observed
    scheduled_but_not_observed: List[DGCAScheduledFlight] = [
        f for k, f in approved_by_flight_key.items() if k not in matched_scheduled_keys
    ]

    total_approved = len(approved_active)
    observed_count = len(matched_scheduled_keys)
    coverage = (observed_count / total_approved) if total_approved > 0 else 1.0

    return ScraperCoverageReport(
        route_id=norm_route,
        travel_date=travel_date,
        dgca_approved_active_flights=total_approved,
        observed_active_flights=observed_count,
        coverage_metric=round(coverage, 4),
        scheduled_and_observed_count=len(observed_and_scheduled),
        scheduled_but_not_observed_count=len(scheduled_but_not_observed),
        unscheduled_observed_count=len(unscheduled_observed),
        scheduled_and_observed=observed_and_scheduled,
        scheduled_but_not_observed=scheduled_but_not_observed,
        unscheduled_observed=unscheduled_observed,
        departure_band_mismatches=departure_band_mismatches,
    )
