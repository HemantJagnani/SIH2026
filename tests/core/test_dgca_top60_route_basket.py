"""
Unit and Integration Tests for DGCA CY2024 Top-60 Route Basket Integration.

Validates:
1. Basket contains exactly 60 routes.
2. Route weights sum to exactly 1.0 within strict Decimal tolerance.
3. Ranks 1 to 60 are preserved and contiguous.
4. Route duplication (unordered pairs) is strictly rejected.
5. Airport distinctions are preserved: DABOLIM (GOI) and GOA / MOPA (GOX) remain separate.
6. Anti-contamination: MoSPI CPI airfare expenditure weight (0.02951% / 0.0002951) cannot contaminate route weights.
7. Weighted aggregation produces expected mathematical results using a deterministic fixture.
8. Bidirectional route resolution (e.g. DEL-BLR <-> BLR-DEL).
9. Full metadata and provenance validation (57.0247% coverage, CY2024, DGCA).
"""

from decimal import Decimal
import pytest
from pydantic import ValidationError

from index.route_basket import (
    BASKET_ID,
    REFERENCE_PERIOD,
    BASKET_SIZE,
    SOURCE,
    COVERAGE_PERCENT,
    TOTAL_BASKET_PASSENGER_VOLUME,
    TOTAL_ALL_INDIA_PASSENGER_VOLUME,
    DGCARouteItem,
    DGCARouteBasketConfig,
    get_dgca_cy2024_top60_basket,
    get_top60_route_weights,
    validate_route_basket,
    assert_no_cpi_weight_contamination,
)
from index.weights import WeightRegistry, normalize_and_validate_weights
from index.aggregation import IndexAggregationEngine
from index.models import RouteIndexResult


def test_basket_contains_exactly_60_routes():
    """Verify that the official DGCA CY2024 basket contains exactly 60 routes."""
    basket = get_dgca_cy2024_top60_basket()
    assert len(basket.routes) == 60
    assert basket.basket_size == 60
    assert basket.basket_id == "DGCA_CY2024_TOP60"
    assert basket.reference_period == "CY2024"
    assert basket.coverage_percent == Decimal("57.0247")
    assert basket.total_basket_passenger_volume == 91995307
    assert basket.total_all_india_passenger_volume == 161325253


def test_weights_sum_to_one():
    """Verify route weights sum to exactly 1.0 under Decimal arithmetic."""
    basket = get_dgca_cy2024_top60_basket()
    weights = [r.route_weight for r in basket.routes]
    
    # All weights must be strictly positive
    for w in weights:
        assert w > Decimal("0"), f"Weight {w} is not positive"

    total_sum = sum(weights)
    assert abs(total_sum - Decimal("1.0")) < Decimal("0.000000000001")

    # Also verify dictionary lookup
    weights_dict = get_top60_route_weights(use_iata_codes=True)
    assert len(weights_dict) == 60
    assert abs(sum(weights_dict.values()) - Decimal("1.0")) < Decimal("0.000000000001")


def test_ranking_preserved():
    """Verify rank order and volume monotonicity from rank 1 to 60."""
    basket = get_dgca_cy2024_top60_basket()
    
    ranks = [r.rank for r in basket.routes]
    assert ranks == list(range(1, 61)), "Ranks must be strictly 1..60"

    # Monotonically non-increasing passenger volumes
    volumes = [r.annual_passenger_volume for r in basket.routes]
    for i in range(len(volumes) - 1):
        assert volumes[i] >= volumes[i + 1], f"Volume inversion between rank {i+1} and {i+2}"

    # Verify top-3 core routes
    assert basket.routes[0].route_id == "DEL-BOM"
    assert basket.routes[0].annual_passenger_volume == 6885053
    assert basket.routes[1].route_id == "BLR-DEL"
    assert basket.routes[1].annual_passenger_volume == 4761622
    assert basket.routes[2].route_id == "BLR-BOM"
    assert basket.routes[2].annual_passenger_volume == 4245720


def test_route_duplication_rejected():
    """Verify that duplicate unordered city-pairs are strictly rejected by the validator."""
    basket = get_dgca_cy2024_top60_basket()
    routes_copy = list(basket.routes)

    # Attempt to inject duplicate unordered route (e.g. BOM-DEL when DEL-BOM exists)
    dup_item = DGCARouteItem(
        rank=60,
        route_id="BOM-DEL",
        origin="MUMBAI",
        destination="DELHI",
        origin_code="BOM",
        destination_code="DEL",
        annual_passenger_volume=100000,
        dgca_share_percent=Decimal("0.1"),
        route_weight=Decimal("0.01"),
        source="DGCA",
        reference_period="CY2024",
        basket_id="DGCA_CY2024_TOP60",
    )
    routes_with_dup = routes_copy[:-1] + [dup_item]
    invalid_basket = basket.model_copy(update={"routes": routes_with_dup})

    with pytest.raises(ValueError, match="Duplicate unordered route detected"):
        validate_route_basket(invalid_basket)


def test_dabolim_mopa_remain_distinct():
    """Verify that South Goa (Dabolim - GOI) and North Goa (Mopa - GOX) remain separate stations."""
    basket = get_dgca_cy2024_top60_basket()
    
    dabolim_routes = [r for r in basket.routes if r.origin_code == "GOI" or r.destination_code == "GOI"]
    mopa_routes = [r for r in basket.routes if r.origin_code == "GOX" or r.destination_code == "GOX"]

    assert len(dabolim_routes) >= 4, "Expected at least 4 Dabolim routes in Top 60"
    assert len(mopa_routes) >= 2, "Expected at least 2 Mopa routes in Top 60"

    # Specific routes must remain separate
    del_goi = next(r for r in basket.routes if r.route_id == "DEL-GOI")
    del_gox = next(r for r in basket.routes if r.route_id == "DEL-GOX")
    bom_goi = next(r for r in basket.routes if r.route_id == "BOM-GOI")
    bom_gox = next(r for r in basket.routes if r.route_id == "BOM-GOX")

    assert del_goi.origin != del_gox.origin or del_goi.destination != del_gox.destination or del_goi.route_id != del_gox.route_id
    assert bom_goi.route_id != bom_gox.route_id
    assert del_goi.annual_passenger_volume == 1607773
    assert del_gox.annual_passenger_volume == 949836


def test_cpi_weight_cannot_contaminate_route_weights():
    """Verify anti-contamination: MoSPI CPI expenditure weight (0.02951% / 0.0002951) fails loudly if used as route weight."""
    # 1. Prohibited item code
    with pytest.raises(ValueError, match="CRITICAL METHODOLOGICAL VIOLATION"):
        assert_no_cpi_weight_contamination({"07.3.3.1.2.01": Decimal("0.5"), "DEL-BOM": Decimal("0.5")})

    # 2. Prohibited decimal weight
    with pytest.raises(ValueError, match="matches CPI airfare expenditure weight"):
        assert_no_cpi_weight_contamination({"DEL-BOM": Decimal("0.0002951")})

    # 3. Prohibited percentage weight
    with pytest.raises(ValueError, match="matches CPI airfare expenditure weight"):
        assert_no_cpi_weight_contamination({"DEL-BOM": Decimal("0.02951")})

    # 4. Prohibited key names
    with pytest.raises(ValueError, match="CRITICAL METHODOLOGICAL VIOLATION"):
        assert_no_cpi_weight_contamination({"CPI_AIRFARE_WEIGHT": Decimal("0.5")})


def test_weighted_aggregation_produces_expected_result_fixture():
    """
    Deterministic fixture test:
    Given 3 available routes with known annual passenger volumes from Top 60:
      - DEL-BOM: 6,885,053 (share among three: 6,885,053 / 15,892,395 = 0.433230)
      - BLR-DEL: 4,761,622 (share among three: 4,761,622 / 15,892,395 = 0.299616)
      - BLR-BOM: 4,245,720 (share among three: 4,245,720 / 15,892,395 = 0.267154)
    With route indices:
      - DEL-BOM = 105.0000
      - BLR-DEL = 110.0000
      - BLR-BOM = 95.0000
    Expected aggregate index:
      105.0 * 0.433230 + 110.0 * 0.299616 + 95.0 * 0.267154 = 103.8265
    """
    weights_reg = WeightRegistry(is_single_route_pilot=False)
    assert weights_reg.basket_id == "DGCA_CY2024_TOP60"

    aggregator = IndexAggregationEngine(weights=weights_reg)

    route_results = {
        "DEL-BOM": RouteIndexResult(
            route="DEL-BOM", period="2026-09", index_value=Decimal("105.0000")
        ),
        "BLR-DEL": RouteIndexResult(
            route="BLR-DEL", period="2026-09", index_value=Decimal("110.0000")
        ),
        "BLR-BOM": RouteIndexResult(
            route="BLR-BOM", period="2026-09", index_value=Decimal("95.0000")
        ),
    }

    result = aggregator.aggregate_routes_to_apix(
        route_results=route_results,
        period="2026-09",
        prev_apix_val=Decimal("100.0000"),
    )

    # Mathematical expectation
    expected_val = (
        Decimal("105.0000") * Decimal("0.433230")
        + Decimal("110.0000") * Decimal("0.299616")
        + Decimal("95.0000") * Decimal("0.267154")
    )
    expected_rounded = Decimal(str(round(expected_val, 4)))

    assert result.index_value == expected_rounded
    assert result.route_basket_id == "DGCA_CY2024_TOP60"
    assert result.route_basket_reference_period == "CY2024"
    assert result.route_basket_coverage_percent == Decimal("57.0247")
    assert "DEL-BOM" in result.route_weights_used
    assert "BLR-DEL" in result.route_weights_used
    assert "BLR-BOM" in result.route_weights_used
    assert abs(sum(result.route_weights_used.values()) - 1.0) < 1e-5


def test_bidirectional_route_resolution():
    """Verify that querying reversed route IDs resolves properly (e.g. DEL-BLR vs BLR-DEL)."""
    weights_reg = WeightRegistry(is_single_route_pilot=False)
    
    # In Top 60, route is registered as BLR-DEL
    w_blr_del = weights_reg.get_route_weight("BLR-DEL")
    w_del_blr = weights_reg.get_route_weight("DEL-BLR")

    assert w_blr_del > Decimal("0")
    assert w_blr_del == w_del_blr, "Bidirectional route lookup must resolve to the identical weight"

    # Sub-weights resolution with reversed key
    sub_norm = weights_reg.get_normalized_sub_weights(["DEL-BLR", "DEL-BOM"], weights_reg.route_weights)
    assert len(sub_norm) == 2
    assert abs(sum(sub_norm.values()) - Decimal("1.0")) < Decimal("1e-6")


def test_provenance_and_metadata_complete():
    """Verify that provenance metadata is complete with authority, files, and methodology."""
    basket = get_dgca_cy2024_top60_basket()
    prov = basket.provenance

    assert prov["authority"] == "Directorate General of Civil Aviation (DGCA), Government of India"
    assert prov["reference_period"] == "CY2024 (January 2024 – December 2024)"
    assert len(prov["source_files"]) == 12
    assert "extraction_methodology" in prov
    assert "normalization_notes" in prov
    assert len(prov["normalization_notes"]) >= 5
