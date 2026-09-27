"""
Tests for DGCA CY2024 Approved Flight Schedule Universe Integration.

Verifies:
1. Station disambiguation (strict separation of GOI vs GOX and DEL vs HDO).
2. Frequency parsing across various formats (daily, weekdays, weekends, specific days).
3. Seasonal validity & operating day matching (Summer 2024, Winter 2024).
4. Flight number normalization and matching.
5. Scraper universe coverage metric (observed_active_flights / DGCA_approved_active_flights).
6. Flight universe tripartite partitioning:
   - OBSERVED_AND_SCHEDULED
   - SCHEDULED_BUT_NOT_OBSERVED
   - UNSCHEDULED_OBSERVED
7. Departure-time band validation against standard APIx bands.
8. Anti-contamination guards (ensuring schedules are strictly control datasets and never fare/route weights).
"""

from datetime import date, datetime, timezone
from decimal import Decimal
import pytest

from index.flight_schedule import (
    AmbiguousStationError,
    DGCAScheduledFlight,
    DGCAScheduleRegistry,
    FlightUniverseStatus,
    ScheduleContaminationError,
    assert_no_schedule_weight_contamination,
    evaluate_scraper_coverage,
    get_schedule_registry,
    is_flight_active_on_date,
    normalize_flight_number,
    normalize_station,
    parse_frequency,
)
from models.canonical import classify_departure_time_band


# ==============================================================================
# 1. STATION DISAMBIGUATION & NORMALIZATION TESTS
# ==============================================================================

def test_station_normalization_goa_separation():
    """Dabolim (GOI) and Mopa (GOX) must be strictly distinguished and never merged."""
    # South Goa Dabolim
    assert normalize_station("DABOLIM") == "GOI"
    assert normalize_station("GOA (DABOLIM)") == "GOI"
    assert normalize_station("GOA DABOLIM") == "GOI"
    assert normalize_station("SOUTH GOA") == "GOI"
    assert normalize_station("GOI") == "GOI"

    # North Goa Manohar International Mopa
    assert normalize_station("MOPA") == "GOX"
    assert normalize_station("GOA (MOPA)") == "GOX"
    assert normalize_station("GOA MOPA") == "GOX"
    assert normalize_station("MANOHAR") == "GOX"
    assert normalize_station("MANOHAR INTERNATIONAL") == "GOX"
    assert normalize_station("NORTH GOA") == "GOX"
    assert normalize_station("GOX") == "GOX"

    # They must never be equal
    assert normalize_station("DABOLIM") != normalize_station("MOPA")

    # Unadorned 'GOA' must raise AmbiguousStationError to prevent accidental conflation
    with pytest.raises(AmbiguousStationError) as exc_info:
        normalize_station("GOA")
    assert "Ambiguous station 'GOA'" in str(exc_info.value)


def test_station_normalization_delhi_hindon_separation():
    """Delhi IGI (DEL) and Hindon (HDO) must be strictly distinguished and never merged."""
    assert normalize_station("DELHI") == "DEL"
    assert normalize_station("NEW DELHI") == "DEL"
    assert normalize_station("INDIRA GANDHI") == "DEL"
    assert normalize_station("DEL") == "DEL"

    assert normalize_station("HINDON") == "HDO"
    assert normalize_station("GHAZIABAD") == "HDO"
    assert normalize_station("HDO") == "HDO"

    assert normalize_station("DELHI") != normalize_station("HINDON")


def test_station_normalization_major_metro_cities():
    """Verifies standard city name normalization for major hubs."""
    assert normalize_station("MUMBAI") == "BOM"
    assert normalize_station("BOMBAY") == "BOM"
    assert normalize_station("BENGALURU") == "BLR"
    assert normalize_station("BANGALORE") == "BLR"
    assert normalize_station("KOLKATA") == "CCU"
    assert normalize_station("CALCUTTA") == "CCU"
    assert normalize_station("HYDERABAD") == "HYD"
    assert normalize_station("CHENNAI") == "MAA"
    assert normalize_station("MADRAS") == "MAA"
    assert normalize_station("AHMEDABAD") == "AMD"


# ==============================================================================
# 2. FREQUENCY PARSING TESTS
# ==============================================================================

def test_frequency_parsing_daily():
    """Daily flights operating all 7 days."""
    assert parse_frequency("1234567") == {1, 2, 3, 4, 5, 6, 7}
    assert parse_frequency("DAILY") == {1, 2, 3, 4, 5, 6, 7}
    assert parse_frequency("1-7") == {1, 2, 3, 4, 5, 6, 7}
    assert parse_frequency(1234567) == {1, 2, 3, 4, 5, 6, 7}


def test_frequency_parsing_weekdays_and_weekends():
    """Weekday-only and weekend-only flights."""
    assert parse_frequency("12345") == {1, 2, 3, 4, 5}
    assert parse_frequency("1-5") == {1, 2, 3, 4, 5}
    assert parse_frequency("WEEKDAYS") == {1, 2, 3, 4, 5}

    assert parse_frequency("67") == {6, 7}
    assert parse_frequency("6-7") == {6, 7}
    assert parse_frequency("WEEKENDS") == {6, 7}


def test_frequency_parsing_specific_days():
    """Specific operating day patterns (e.g. Mon/Wed/Fri, Tue/Thu/Sat)."""
    assert parse_frequency("135") == {1, 3, 5}
    assert parse_frequency("246") == {2, 4, 6}
    assert parse_frequency("7") == {7}
    assert parse_frequency([1, 3, 5]) == {1, 3, 5}


# ==============================================================================
# 3. SEASONAL & OPERATING DAY VALIDITY TESTS
# ==============================================================================

def test_flight_seasonal_and_day_validity():
    """Verifies that is_flight_active_on_date checks both date range and weekday."""
    # Summer 2024 flight operating Mon, Wed, Fri only
    flight_summer = DGCAScheduledFlight(
        schedule_id="DGCA-S24-UK-975",
        season="SUMMER_2024",
        operator_code="UK",
        airline="Vistara",
        flight_no="UK 975",
        origin_city="DELHI",
        destination_city="MUMBAI",
        origin_code="DEL",
        destination_code="BOM",
        route_id="DEL-BOM",
        departure_time="15:45",
        arrival_time="18:00",
        frequency="135",
        effective_from=date(2024, 3, 31),
        effective_to=date(2024, 10, 26),
    )

    # 2024-06-12 is Wednesday (ISO day 3) -> should be active
    assert date(2024, 6, 12).isoweekday() == 3
    assert is_flight_active_on_date(flight_summer, date(2024, 6, 12)) is True

    # 2024-06-13 is Thursday (ISO day 4) -> NOT in frequency 135 -> inactive
    assert date(2024, 6, 13).isoweekday() == 4
    assert is_flight_active_on_date(flight_summer, date(2024, 6, 13)) is False

    # 2024-11-15 is in Winter 2024 -> out of date range -> inactive
    assert is_flight_active_on_date(flight_summer, date(2024, 11, 15)) is False

    # Winter 2024 flight operating daily
    flight_winter = DGCAScheduledFlight(
        schedule_id="DGCA-W24-6E-2045",
        season="WINTER_2024",
        operator_code="6E",
        airline="IndiGo",
        flight_no="6E 2045",
        origin_city="DELHI",
        destination_city="MUMBAI",
        origin_code="DEL",
        destination_code="BOM",
        route_id="DEL-BOM",
        departure_time="04:45",
        arrival_time="07:00",
        frequency="1234567",
        effective_from=date(2024, 10, 27),
        effective_to=date(2025, 3, 29),
    )

    # 2024-11-15 is active in Winter 2024
    assert is_flight_active_on_date(flight_winter, date(2024, 11, 15)) is True
    # 2024-06-12 is before Winter 2024 starts -> inactive
    assert is_flight_active_on_date(flight_winter, date(2024, 6, 12)) is False


# ==============================================================================
# 4. FLIGHT NUMBER NORMALIZATION TESTS
# ==============================================================================

def test_normalize_flight_number():
    """Tests normalizations with spaces, dashes, uppercase/lowercase, and hints."""
    assert normalize_flight_number("6E 2045") == ("6E", "2045")
    assert normalize_flight_number("6E-2045") == ("6E", "2045")
    assert normalize_flight_number("6e2045") == ("6E", "2045")
    assert normalize_flight_number("AI 887") == ("AI", "887")
    assert normalize_flight_number("ai-887") == ("AI", "887")
    assert normalize_flight_number("UK 995") == ("UK", "995")
    assert normalize_flight_number("QP 1102") == ("QP", "1102")

    # Numeric only with airline hint
    assert normalize_flight_number("2045", airline_hint="IndiGo") == ("6E", "2045")
    assert normalize_flight_number("887", airline_hint="Air India") == ("AI", "887")


# ==============================================================================
# 5. REGISTRY LOADING & QUERY TESTS
# ==============================================================================

def test_schedule_registry_loading():
    """Verifies that the reference schedule dataset loads and contains key routes."""
    registry = get_schedule_registry()
    assert len(registry.flights) > 50
    assert registry.dataset_metadata["dataset_id"] == "DGCA_DOMESTIC_SCHEDULE_CY2024"
    assert registry.dataset_metadata["reference_year"] == 2024

    # Check key routes exist
    del_bom_flights = registry.get_flights_for_route("DEL-BOM")
    assert len(del_bom_flights) >= 10

    blr_del_flights = registry.get_flights_for_route("BLR-DEL")
    assert len(blr_del_flights) >= 5

    # Check separate Goa routes exist
    bom_goi_flights = registry.get_flights_for_route("BOM-GOI")
    bom_gox_flights = registry.get_flights_for_route("BOM-GOX")
    assert len(bom_goi_flights) >= 2
    assert len(bom_gox_flights) >= 3

    # Check Hindon route exists
    hdo_ixl_flights = registry.get_flights_for_route("HDO-IXL")
    assert len(hdo_ixl_flights) >= 1


# ==============================================================================
# 6. SCRAPER COVERAGE & UNIVERSE PARTITIONING TESTS
# ==============================================================================

def test_scraper_coverage_and_tripartite_partitioning():
    """
    Tests evaluation of scraper observations against approved active flights:
    - Calculates observed_active_flights / DGCA_approved_active_flights
    - Distinguishes:
      * scheduled and observed
      * scheduled but not observed
      * unscheduled observed
    """
    registry = get_schedule_registry()
    travel_date = date(2024, 6, 12)  # Wednesday in Summer 2024
    route = "DEL-BOM"

    active_approved = registry.get_active_flights(route, travel_date)
    total_approved = len(active_approved)
    assert total_approved > 5

    # Suppose scraper captures:
    # 1. First 4 approved flights
    # 2. Plus 1 ad-hoc flight not in the schedule (e.g. 6E 9999)
    # This leaves total_approved - 4 flights missed.
    scraped_sample = []
    for f in active_approved[:4]:
        scraped_sample.append({
            "airline": f.airline,
            "flight_number": f.flight_no,
            "departure_time": f.departure_time,
            "origin": "DEL",
            "destination": "BOM",
        })

    # Add unscheduled flight
    scraped_sample.append({
        "airline": "IndiGo",
        "flight_number": "6E 9999",
        "departure_time": "12:00",
        "origin": "DEL",
        "destination": "BOM",
    })

    report = evaluate_scraper_coverage(
        scraped_observations=scraped_sample,
        route_id=route,
        travel_date=travel_date,
        registry=registry,
    )

    # Denominator
    assert report.dgca_approved_active_flights == total_approved
    # Numerator (observed & scheduled)
    assert report.observed_active_flights == 4
    # Coverage metric
    expected_coverage = round(4 / total_approved, 4)
    assert report.coverage_metric == expected_coverage

    # Tripartite counts
    assert report.scheduled_and_observed_count == 4
    assert report.scheduled_but_not_observed_count == total_approved - 4
    assert report.unscheduled_observed_count == 1

    # Status verifications
    assert all(r.status == FlightUniverseStatus.OBSERVED_AND_SCHEDULED for r in report.scheduled_and_observed)
    assert len(report.scheduled_but_not_observed) == total_approved - 4
    assert report.unscheduled_observed[0].status == FlightUniverseStatus.UNSCHEDULED_OBSERVED
    assert report.unscheduled_observed[0].observed_flight_number == "6E 9999"


# ==============================================================================
# 7. DEPARTURE-TIME BAND VALIDATION TESTS
# ==============================================================================

def test_departure_time_band_validation():
    """
    Verifies that scraper departure times are validated against official
    DGCA scheduled departure time bands.
    """
    registry = get_schedule_registry()
    travel_date = date(2024, 6, 12)
    route = "DEL-BOM"

    active_approved = registry.get_active_flights(route, travel_date)
    # Find 6E 5021 scheduled at 06:15 (MORNING band)
    target_flt = next(f for f in active_approved if "5021" in f.flight_no)
    assert target_flt.departure_time == "06:15"
    assert target_flt.departure_time_band == "MORNING"

    # Case 1: Scraped departure time matches MORNING band (e.g. 06:20)
    scraped_matching = [{
        "airline": target_flt.airline,
        "flight_number": target_flt.flight_no,
        "departure_time": "06:20",
    }]
    report1 = evaluate_scraper_coverage(scraped_matching, route, travel_date, registry)
    assert len(report1.departure_band_mismatches) == 0
    assert report1.scheduled_and_observed[0].band_matches is True

    # Case 2: Scraped departure time moved to EARLY_MORNING (e.g. 05:30)
    scraped_shifted = [{
        "airline": target_flt.airline,
        "flight_number": target_flt.flight_no,
        "departure_time": "05:30",
    }]
    report2 = evaluate_scraper_coverage(scraped_shifted, route, travel_date, registry)
    assert len(report2.departure_band_mismatches) == 1
    mismatch = report2.departure_band_mismatches[0]
    assert mismatch.band_matches is False
    assert mismatch.scheduled_time_band == "MORNING"
    assert mismatch.observed_time_band == "EARLY_MORNING"


# ==============================================================================
# 8. ANTI-CONTAMINATION METHODOLOGICAL SAFEGUARD TESTS
# ==============================================================================

def test_anti_contamination_guard():
    """
    Verifies that flight schedule universe records cannot be used as
    fare weights, route weights, lead-time weights, or CPI weights.
    """
    # Clean route weights should pass
    clean_weights = {
        "DEL-BOM": Decimal("0.07484135"),
        "BLR-DEL": Decimal("0.05175940"),
    }
    assert_no_schedule_weight_contamination(clean_weights)

    # Injected schedule ID should raise ScheduleContaminationError
    contaminated_weights = {
        "DEL-BOM": Decimal("0.07484135"),
        "DGCA-S24-6E-2045": Decimal("0.05175940"),
    }
    with pytest.raises(ScheduleContaminationError) as exc_info:
        assert_no_schedule_weight_contamination(contaminated_weights)
    assert "CRITICAL METHODOLOGICAL VIOLATION" in str(exc_info.value)

    contaminated_weights_prefix = {
        "SCHEDULE_FREQ_WEIGHT": Decimal("0.50"),
    }
    with pytest.raises(ScheduleContaminationError) as exc_info:
        assert_no_schedule_weight_contamination(contaminated_weights_prefix)
    assert "cannot be used as a pricing, route, or expenditure weight" in str(exc_info.value)
