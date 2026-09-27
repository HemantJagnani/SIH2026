"""
Test Suite for Official MoSPI CPI 2024 Domestic Airfare Expenditure Weight Integration.

Validates the strict architectural separation and mathematical integrity specified in requirements:
1. Correct weight loading (Item 07.3.3.1.2.01, 0.02951%, decimal 0.0002951)
2. Percentage/decimal consistency and loud failure on disagreement
3. Correct CPI contribution calculation (airfare_contribution_pp = APIx_percent_change * 0.02951 / 100)
4. Protection against using CPI weight as route weight or multiplying fare observations
5. Missing/invalid weight handling
6. Distinct separation of APIx level, MoM %, YoY %, CPI weight, and CPI contribution outputs
"""

from decimal import Decimal
import pytest

from index import (
    APIxEngine,
    WeightRegistry,
    normalize_and_validate_weights,
    assert_no_cpi_weight_contamination,
    CPIIntegrationLayer,
    CPIAirfareWeightConfig,
    CPI_AIRFARE_WEIGHT_PERCENT,
    CPI_AIRFARE_WEIGHT_DECIMAL,
    CPI_AIRFARE_ITEM_CODE,
    CPI_AIRFARE_ITEM_DESCRIPTION,
    CPI_REFERENCE_YEAR,
    CPI_WEIGHT_SOURCE,
    CPI_AIRFARE_DISCLAIMER,
)
from models.canonical import NormalizedFareObservation
from datetime import date, datetime


def make_sample_obs(fare: Decimal, month: str = "2026-08") -> NormalizedFareObservation:
    y, m = map(int, month.split("-"))
    day_map = {8: 19, 9: 16, 10: 14}
    day = day_map.get(m, 16)
    return NormalizedFareObservation(
        origin="DEL",
        destination="BOM",
        route="DEL-BOM",
        travel_date=date(y, m, day),
        lead_days=21,
        lead_time_class="T+21",
        airline="IndiGo",
        airline_code="6E",
        flight_number="6E-101",
        departure_time_local=datetime(y, m, day, 6, 0),
        arrival_time_local=datetime(y, m, day, 8, 15),
        stops=0,
        fare_family="Saver",
        fare_family_group="STANDARD_SAVER",
        total_fare=fare,
        normalized_price_inr=fare,
        currency="INR",
        source="google_flights",
        source_itinerary_id="ITIN_6E_101",
        source_offer_id="OFFER_6E_101",
        quality_status="VALID",
        collection_run_id="825fa969-5811-49c8-9854-40637fd438a2",
    )


# ------------------------------------------------------------------------------
# 1. Correct Weight Loading
# ------------------------------------------------------------------------------
def test_cpi_airfare_weight_loading():
    """Verifies that the official CPI 2024 airfare weight loads with exact metadata."""
    cfg = CPIAirfareWeightConfig()
    
    assert cfg.percentage_weight == Decimal("0.02951")
    assert cfg.decimal_weight == Decimal("0.0002951")
    assert cfg.item_code == "07.3.3.1.2.01"
    assert cfg.description == "Passenger transport by air, domestic"
    assert cfg.reference_year == 2024
    assert cfg.source == "MoSPI CPI 2024 Weights of item CPI 2024"
    assert "announcements_1769773015355" in cfg.provenance_reference
    assert "Weights_of_itme_CPI_2024.xlsx" in cfg.provenance_reference
    assert "The MoSPI CPI 2024 airfare expenditure weight is used only" in cfg.disclaimer
    assert "It is not used to construct the Airfare Price Index itself." in cfg.disclaimer

    # Verify metadata dictionary export
    meta = cfg.to_metadata_dict()
    assert meta["percentage_weight"] == 0.02951
    assert meta["decimal_weight"] == 0.0002951
    assert meta["item_code"] == "07.3.3.1.2.01"
    assert meta["reference_year"] == 2024
    assert meta["disclaimer"] == cfg.disclaimer


# ------------------------------------------------------------------------------
# 2. Percentage / Decimal Consistency & Loud Failure on Disagreement
# ------------------------------------------------------------------------------
def test_percentage_decimal_consistency_validation():
    """Verifies that percentage and decimal representations must agree exactly."""
    # 0.02951% in decimal is 0.0002951
    assert Decimal("0.02951") / Decimal("100") == Decimal("0.0002951")

    # If percentage and decimal disagree, must fail loudly
    with pytest.raises(ValueError, match="disagree"):
        CPIAirfareWeightConfig(
            percentage_weight=Decimal("0.02951"),
            decimal_weight=Decimal("0.0005000"),  # Disagrees
        )

    # If percentage is not 0.02951, must fail loudly
    with pytest.raises(ValueError, match="Invalid CPI airfare percentage weight"):
        CPIAirfareWeightConfig(
            percentage_weight=Decimal("0.03500"),
            decimal_weight=Decimal("0.0003500"),
        )

    # If decimal representation differs from percentage, must fail loudly with disagreement
    with pytest.raises(ValueError, match="disagree"):
        CPIAirfareWeightConfig(
            percentage_weight=Decimal("0.02951"),
            decimal_weight=Decimal("0.0002950"),
        )

    # Non-Decimal types rejected
    with pytest.raises(TypeError, match="must be of type Decimal"):
        CPIAirfareWeightConfig(
            percentage_weight="0.02951",  # type: ignore
            decimal_weight=Decimal("0.0002951"),
        )

    # If item code is wrong, must fail loudly
    with pytest.raises(ValueError, match="Invalid CPI item code"):
        CPIAirfareWeightConfig(
            item_code="07.3.3.1.01",  # Obsolete provisional code
        )

    # If reference year is wrong, must fail loudly
    with pytest.raises(ValueError, match="Invalid CPI reference year"):
        CPIAirfareWeightConfig(
            reference_year=2012,
        )


# ------------------------------------------------------------------------------
# 3. Correct CPI Contribution Calculation
# ------------------------------------------------------------------------------
def test_cpi_contribution_calculation():
    """
    Given APIx percentage change:
        airfare_contribution_pp = APIx_percent_change * 0.02951 / 100

    Example from specification:
        APIx change = +10%
        contribution = 10 * 0.02951 / 100
                     = +0.002951 percentage points
    """
    cfg = CPIAirfareWeightConfig()

    # Specification example: +10% change
    contrib_10 = cfg.calculate_cpi_contribution_pp(Decimal("10.0"))
    assert contrib_10 == Decimal("0.00295100")

    # Float and int input compatibility
    assert cfg.calculate_cpi_contribution_pp(10) == Decimal("0.00295100")
    assert cfg.calculate_cpi_contribution_pp(10.0) == Decimal("0.00295100")
    assert cfg.calculate_cpi_contribution_pp("10.0") == Decimal("0.00295100")

    # Negative inflation rate: -5.0%
    contrib_neg = cfg.calculate_cpi_contribution_pp(Decimal("-5.0"))
    # -5 * 0.02951 / 100 = -0.0014755
    assert contrib_neg == Decimal("-0.00147550")

    # Zero inflation
    contrib_zero = cfg.calculate_cpi_contribution_pp(Decimal("0.0"))
    assert contrib_zero == Decimal("0.00000000")

    # None input handling
    assert cfg.calculate_cpi_contribution_pp(None) == Decimal("0.00000000")


# ------------------------------------------------------------------------------
# 4. Protection Against Using CPI Weight as Route Weight
# ------------------------------------------------------------------------------
def test_protection_against_cpi_weight_as_route_weight():
    """
    CPI airfare weight (0.02951% / 0.0002951) must NEVER be used as a route weight.
    Attempts to inject it into route weights or WeightRegistry must raise ValueError loudly.
    """
    # Attempting to normalize weights containing CPI expenditure weight value
    with pytest.raises(ValueError, match="CRITICAL METHODOLOGICAL VIOLATION"):
        normalize_and_validate_weights({
            "DEL-BOM": Decimal("0.0002951"),  # Accidental injection
            "DEL-BLR": Decimal("0.9997049"),
        })

    with pytest.raises(ValueError, match="CRITICAL METHODOLOGICAL VIOLATION"):
        normalize_and_validate_weights({
            "DEL-BOM": Decimal("0.02951"),  # Accidental percentage injection
            "DEL-BLR": Decimal("0.97049"),
        })

    # Attempting to use CPI item code as route key
    with pytest.raises(ValueError, match="CRITICAL METHODOLOGICAL VIOLATION"):
        normalize_and_validate_weights({
            "07.3.3.1.2.01": Decimal("1.000000"),
        })

    with pytest.raises(ValueError, match="CRITICAL METHODOLOGICAL VIOLATION"):
        WeightRegistry(route_weights={
            "07.3.3.1.2.01": Decimal("1.000000"),
        })

    # Explicit direct helper
    with pytest.raises(ValueError, match="CRITICAL METHODOLOGICAL VIOLATION"):
        assert_no_cpi_weight_contamination({"CPI_AIRFARE_WEIGHT": 0.5, "DEL-BOM": 0.5})


# ------------------------------------------------------------------------------
# 5. APIx Construction Independence (Never multiplies fare obs by 0.0002951)
# ------------------------------------------------------------------------------
def test_apix_construction_independence_from_cpi_weight():
    """
    Verifies that:
    - Route weights and lead-time weights alone govern APIx price index calculation.
    - Fare observations (e.g. ₹5,000) are NEVER multiplied by 0.0002951 during index construction.
    """
    engine = APIxEngine()

    # Base period t0: fare = ₹5,000
    obs_t0 = [make_sample_obs(Decimal("5000.00"), month="2026-08")]
    r0 = engine.process_period("2026-08", obs_t0)
    assert r0.index_value == Decimal("100.00")

    # Period t1: fare increases +10% from ₹5,000 to ₹5,500
    obs_t1 = [make_sample_obs(Decimal("5500.00"), month="2026-09")]
    r1 = engine.process_period("2026-09", obs_t1, prev_period="2026-08")

    # APIx index value must be exactly 110.0000 (+10%), NOT multiplied by 0.0002951!
    assert r1.index_value == Decimal("110.0000")
    assert r1.mom_percent == Decimal("10.0000")

    # Jevons relative link is 1.100000 (NOT scaled by CPI weight)
    assert r1.elementary_results[0].jevons_link == Decimal("1.100000")


# ------------------------------------------------------------------------------
# 6. Separate Outputs Verification
# ------------------------------------------------------------------------------
def test_separate_outputs_apix_and_cpi_contribution():
    """
    Verifies Requirement 6: Keep APIx and CPI contribution as separate outputs:
    - APIx level
    - APIx month-on-month change
    - APIx year-on-year change
    - CPI airfare weight
    - estimated CPI contribution in percentage points
    """
    engine = APIxEngine()

    obs_t0 = [make_sample_obs(Decimal("6000.00"), month="2026-08")]
    engine.process_period("2026-08", obs_t0)

    # +10% increase in period t1
    obs_t1 = [make_sample_obs(Decimal("6600.00"), month="2026-09")]
    r1 = engine.process_period("2026-09", obs_t1, prev_period="2026-08")

    # 1. APIx Level
    assert r1.index_value == Decimal("110.0000")

    # 2. APIx Month-on-Month Change
    assert r1.mom_percent == Decimal("10.0000")

    # 3. APIx Year-on-Year Change (None for 1-month series)
    assert r1.yoy_percent is None

    # 4. CPI Airfare Weight (Separate distinct output)
    assert r1.cpi_airfare_weight_percent == Decimal("0.02951")
    assert r1.cpi_airfare_weight_decimal == Decimal("0.0002951")
    assert r1.cpi_airfare_item_code == "07.3.3.1.2.01"
    assert r1.cpi_airfare_item_description == "Passenger transport by air, domestic"
    assert r1.cpi_reference_year == 2024
    assert r1.cpi_weight_source == "MoSPI CPI 2024 Weights of item CPI 2024"

    # 5. Estimated CPI Contribution in percentage points (+10% * 0.02951 / 100 = +0.002951 pp)
    assert r1.estimated_cpi_contribution_pp == Decimal("0.00295100")

    # 6. Mandatory disclaimer verified
    assert "The MoSPI CPI 2024 airfare expenditure weight is used only for the optional integration" in r1.cpi_weight_disclaimer
    assert "It is not used to construct the Airfare Price Index itself." in r1.cpi_weight_disclaimer
