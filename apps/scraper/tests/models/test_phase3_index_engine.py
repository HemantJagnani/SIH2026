"""
Unit Tests for APIx Phase 3 Statistical Index Compilation Engine.
Validates:
- Monthly geometric product pricing
- Product matching engine
- Short-chain Jevons elementary links
- Chaining recursion
- Weight normalization & sum-to-one validation
- Lead-time & route aggregations
- Antigravity Acceptance Criteria:
  1. All matched prices unchanged => Jevons link 1.000000
  2. All matched prices rise 10% => Jevons link 1.100000
  3. Chained index equals previous index times link
  4. Route and lead-time weights each sum to 1
  5. Adding duplicate scraped rows does not change the result
  6. T+21 is stored and aggregated as an independent checkpoint
  7. End-to-end execution on real scraped dataset
"""

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
import pytest

from models.canonical import NormalizedFareObservation
from index import (
    MonthlyProductPrice,
    compute_monthly_product_prices,
    ProductMatchingEngine,
    JevonsEngine,
    WeightRegistry,
    normalize_and_validate_weights,
    IndexAggregationEngine,
    APIxEngine,
)


def create_sample_observation(
    flight_num: str,
    fare: Decimal,
    month: str = "2026-09",
    route: str = "DEL-BOM",
    lead_time: str = "T+7",
    quality_status: str = "VALID",
) -> NormalizedFareObservation:
    origin, dest = route.split("-")
    y, m = map(int, month.split("-"))
    # Use Wednesdays for consistent WEEKDAY stratification across months
    day_map = {8: 19, 9: 16, 10: 14}
    day = day_map.get(m, 15)
    travel_date = date(y, m, day)
    return NormalizedFareObservation(
        origin=origin,
        destination=dest,
        route=route,
        travel_date=travel_date,
        lead_days=7 if lead_time == "T+7" else 21,
        lead_time_class=lead_time,
        airline="IndiGo",
        flight_number=flight_num,
        departure_time_local=datetime(y, m, day, 6, 0),
        arrival_time_local=datetime(y, m, day, 8, 15),
        total_fare=fare,
        normalized_price_inr=fare,
        currency="INR",
        source="easemytrip",
        collection_run_id="825fa969-5811-49c8-9854-40637fd438a2",
        quality_status=quality_status,
    )


def test_monthly_geometric_product_pricing():
    """Verify that multiple observations within a month are aggregated via geometric mean."""
    # Product observed 3 times with fares 4000, 6000, 9000
    # Geometric mean = (4000 * 6000 * 9000)^(1/3) = (216,000,000,000)^(1/3) = 6000.00
    obs1 = create_sample_observation("6E-101", Decimal("4000.00"), month="2026-09")
    obs2 = create_sample_observation("6E-101", Decimal("6000.00"), month="2026-09")
    obs3 = create_sample_observation("6E-101", Decimal("9000.00"), month="2026-09")
    # Duplicate or invalid observation should be skipped
    obs_dup = create_sample_observation("6E-101", Decimal("9999.00"), month="2026-09", quality_status="DUPLICATE")

    prices = compute_monthly_product_prices([obs1, obs2, obs3, obs_dup])
    assert len(prices) == 1
    p = list(prices.values())[0]
    assert p.geometric_price == Decimal("6000.00")
    assert p.observation_count == 3


def test_jevons_neutrality_and_ten_percent_shift():
    """Verify Antigravity Acceptance Tests 1 & 2: unchanged prices => link 1.0, +10% => link 1.10."""
    engine = JevonsEngine(base_value=Decimal("100.00"))

    # Period 0 prices
    obs_t0 = [
        create_sample_observation("6E-101", Decimal("5000.00"), month="2026-08"),
        create_sample_observation("6E-102", Decimal("8000.00"), month="2026-08"),
    ]
    prices_t0 = compute_monthly_product_prices(obs_t0)

    # Test 1: Period 1 prices identical to Period 0 => link must be exactly 1.000000
    obs_t1_neutral = [
        create_sample_observation("6E-101", Decimal("5000.00"), month="2026-09"),
        create_sample_observation("6E-102", Decimal("8000.00"), month="2026-09"),
    ]
    prices_t1_neutral = compute_monthly_product_prices(obs_t1_neutral)

    matcher = ProductMatchingEngine()
    matches_neutral = matcher.match_periods(prices_t0, prices_t1_neutral)
    s_id = list(matches_neutral.keys())[0]
    matched_prods, elig_prev, cov, is_pub = matches_neutral[s_id]

    res_neutral = engine.compute_elementary_index(
        stratum_id=s_id,
        route="DEL-BOM",
        lead_time_class="T+7",
        period="2026-09",
        prev_period="2026-08",
        matched_products=matched_prods,
        eligible_count_prev=elig_prev,
        coverage_ratio=cov,
        is_published=is_pub,
    )
    assert res_neutral.jevons_link == Decimal("1.000000")
    assert res_neutral.chained_index == Decimal("100.0000")

    # Test 2: Period 2 prices rise by exactly 10% (5000 -> 5500, 8000 -> 8800)
    obs_t2_shift = [
        create_sample_observation("6E-101", Decimal("5500.00"), month="2026-10"),
        create_sample_observation("6E-102", Decimal("8800.00"), month="2026-10"),
    ]
    prices_t2_shift = compute_monthly_product_prices(obs_t2_shift)
    matches_shift = matcher.match_periods(prices_t1_neutral, prices_t2_shift)
    matched_prods_s, elig_prev_s, cov_s, is_pub_s = matches_shift[s_id]

    res_shift = engine.compute_elementary_index(
        stratum_id=s_id,
        route="DEL-BOM",
        lead_time_class="T+7",
        period="2026-10",
        prev_period="2026-09",
        matched_products=matched_prods_s,
        eligible_count_prev=elig_prev_s,
        coverage_ratio=cov_s,
        is_published=is_pub_s,
    )
    assert res_shift.jevons_link == Decimal("1.100000")
    assert res_shift.chained_index == Decimal("110.0000")  # 100 * 1.10


def test_weights_sum_to_one_validation():
    """Verify Antigravity Acceptance Test 4: weights must sum to 1.0000."""
    registry = WeightRegistry()
    assert sum(registry.route_weights.values()) == Decimal("1.00")
    assert sum(registry.lead_time_weights.values()) == Decimal("1.00")

    # Must contain T+21 MoSPI alignment checkpoint
    assert "T+21" in registry.lead_time_weights
    assert registry.lead_time_weights["T+21"] > Decimal("0")

    # Invalid weights not summing to 1 must raise ValueError
    with pytest.raises(ValueError, match="Weights must sum to 1.0000"):
        normalize_and_validate_weights({"DEL-BOM": Decimal("0.5"), "DEL-BLR": Decimal("0.3")})


def test_duplicate_invariance():
    """Verify Antigravity Acceptance Test 5: adding duplicate rows does not change the index."""
    apix_engine = APIxEngine()

    base_obs = [
        create_sample_observation("6E-101", Decimal("5000.00"), month="2026-08"),
        create_sample_observation("6E-102", Decimal("8000.00"), month="2026-08"),
    ]
    curr_obs = [
        create_sample_observation("6E-101", Decimal("5500.00"), month="2026-09"),
        create_sample_observation("6E-102", Decimal("8800.00"), month="2026-09"),
    ]

    res_clean = apix_engine.process_period("2026-08", base_obs)
    res_clean_t1 = apix_engine.process_period("2026-09", curr_obs, prev_period="2026-08")

    # Now add duplicated rows marked with duplicate quality status
    curr_obs_with_duplicates = curr_obs + [
        create_sample_observation("6E-101", Decimal("5500.00"), month="2026-09", quality_status="DUPLICATE"),
        create_sample_observation("6E-102", Decimal("8800.00"), month="2026-09", quality_status="DUPLICATE"),
    ]

    apix_engine_dups = APIxEngine()
    apix_engine_dups.process_period("2026-08", base_obs)
    res_with_dups = apix_engine_dups.process_period("2026-09", curr_obs_with_duplicates, prev_period="2026-08")

    # Result must be completely identical
    assert res_clean_t1.index_value == res_with_dups.index_value
    assert res_clean_t1.mom_percent == res_with_dups.mom_percent


def test_end_to_end_on_real_easemytrip_dataset():
    """Verify executing complete APIx engine on the real scraped normalized dataset."""
    json_path = Path("easemytrip_normalized_data.json")
    assert json_path.exists(), "easemytrip_normalized_data.json must exist"

    with open(json_path, "r", encoding="utf-8") as f:
        records_json = json.load(f)

    observations = [NormalizedFareObservation(**r) for r in records_json]
    assert len(observations) == 145

    engine = APIxEngine()
    result = engine.process_period(period="2026-09", observations=observations)

    assert result.index_name == "India Airfare Price Index"
    assert result.period == "2026-09"
    assert result.index_value == Decimal("100.00")  # Baseline reference initialization
    assert "DEL-BOM" in result.route_indices
    assert len(result.lead_time_indices) > 0
    assert result.methodology_version == "APIx v1.0"
    assert result.weight_version == "2026.09"
    print(f"\nAPIx Index compiled successfully: {result.index_value}, Routes: {result.route_indices}")
