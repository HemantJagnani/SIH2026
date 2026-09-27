"""
Unit and integration tests for APIx Empirical Lead-Time Weights.

Tests:
1. Basket contains exactly 6 lead times (T+1, T+7, T+15, T+21, T+30, T+45).
2. Weights sum to exactly 1.0 (strict Decimal tolerance).
3. Exact empirical values preserved from Clean_Dataset.csv:
   T+1: 0.0509, T+7: 0.1350, T+15: 0.1491, T+21: 0.1519, T+30: 0.2588, T+45: 0.2543.
4. Methodology status is EMPIRICAL_DATASET_DERIVED_LEAD_TIME_WEIGHTS.
5. Sensitivity-analysis equal-weight configuration preserved and functional.
6. Anti-contamination guard: CPI expenditure weight cannot contaminate lead-time weights.
7. Anti-contamination guard: CPI item code cannot contaminate lead-time weights.
8. Anti-contamination guard: Route weights cannot contaminate lead-time weights.
9. Deterministic aggregation test verifying exact mathematical outcome.
10. End-to-end APIxEngine execution verifying metadata integration.
"""

from decimal import Decimal
import pytest
from index.lead_time_weights import (
    EMPIRICAL_LEAD_TIME_WEIGHTS,
    EQUAL_LEAD_TIME_WEIGHTS,
    LEAD_TIME_CLASSES,
    METHODOLOGY_STATUS_EMPIRICAL,
    METHODOLOGY_STATUS_SENSITIVITY,
    SOURCE_DATASET,
    DISCLAIMER,
    get_empirical_lead_time_weights,
    get_equal_lead_time_weights,
    get_lead_time_weight_config,
    validate_lead_time_weights,
    assert_no_cpi_contamination,
)
from index.weights import WeightRegistry
from index.aggregation import IndexAggregationEngine
from index.engine import APIxEngine
from index.models import ElementaryIndexResult, LeadTimeIndexResult, RouteIndexResult


def test_lead_time_basket_exact_six_classes():
    """Verify exactly 6 lead-time classes exist in canonical order."""
    weights = get_empirical_lead_time_weights()
    assert len(weights) == 6
    assert list(weights.keys()) == ["T+1", "T+7", "T+15", "T+21", "T+30", "T+45"]


def test_empirical_weights_sum_to_one_exact_decimal():
    """Verify empirical lead-time weights sum to exactly Decimal('1.0000')."""
    weights = get_empirical_lead_time_weights()
    total = sum(weights.values())
    assert total == Decimal("1.0000")
    for k, v in weights.items():
        assert v > Decimal("0")


def test_empirical_values_exact_numbers():
    """Verify exact numerical weights matching Clean_Dataset.csv derivation."""
    weights = get_empirical_lead_time_weights()
    assert weights["T+1"] == Decimal("0.0509")
    assert weights["T+7"] == Decimal("0.1350")
    assert weights["T+15"] == Decimal("0.1491")
    assert weights["T+21"] == Decimal("0.1519")
    assert weights["T+30"] == Decimal("0.2588")
    assert weights["T+45"] == Decimal("0.2543")


def test_methodology_status_and_disclaimer():
    """Verify methodology status and mandatory non-official disclaimer."""
    config = get_lead_time_weight_config(mode="empirical")
    assert config.methodology_status == METHODOLOGY_STATUS_EMPIRICAL
    assert config.source_dataset == "Clean_Dataset.csv"
    assert config.is_official_national_weights is False
    assert "not official Indian national booking weights" in config.disclaimer
    assert len(config.items) == 6


def test_sensitivity_equal_weights_preserved():
    """Verify equal weighting (w_L = 1/6) is preserved as sensitivity-analysis configuration."""
    # From config function
    config_eq = get_lead_time_weight_config(mode="sensitivity")
    assert config_eq.methodology_status == METHODOLOGY_STATUS_SENSITIVITY
    assert sum(config_eq.weights.values()) == Decimal("1.000000")

    # In WeightRegistry via mode
    reg_eq = WeightRegistry(lead_time_weight_mode="sensitivity")
    assert reg_eq.lead_time_weight_type == METHODOLOGY_STATUS_SENSITIVITY
    assert sum(reg_eq.lead_time_weights.values()) == Decimal("1.000000")
    for k in LEAD_TIME_CLASSES:
        assert reg_eq.lead_time_weights[k] in (Decimal("0.166667"), Decimal("0.166666"))


def test_anti_contamination_cpi_expenditure_weight():
    """Verify anti-contamination guard rejects MoSPI CPI airfare expenditure weight (0.02951% / 0.0002951)."""
    # Attempt to inject CPI weight 0.0002951
    bad_weights_1 = {
        "T+1": Decimal("0.0002951"),
        "T+7": Decimal("0.1997049"),
        "T+15": Decimal("0.20"),
        "T+21": Decimal("0.20"),
        "T+30": Decimal("0.20"),
        "T+45": Decimal("0.20"),
    }
    with pytest.raises(ValueError, match="matches CPI airfare expenditure weight"):
        validate_lead_time_weights(bad_weights_1)

    # Attempt to inject CPI percentage weight 0.02951
    bad_weights_2 = {
        "T+1": Decimal("0.02951"),
        "T+7": Decimal("0.17049"),
        "T+15": Decimal("0.20"),
        "T+21": Decimal("0.20"),
        "T+30": Decimal("0.20"),
        "T+45": Decimal("0.20"),
    }
    with pytest.raises(ValueError, match="matches CPI airfare expenditure weight"):
        validate_lead_time_weights(bad_weights_2)


def test_anti_contamination_cpi_item_code():
    """Verify rejection of MoSPI CPI 2024 item code as lead-time key."""
    bad_keys = {
        "07.3.3.1.2.01": Decimal("0.50"),
        "T+7": Decimal("0.50"),
    }
    with pytest.raises(ValueError, match="CPI expenditure item code"):
        validate_lead_time_weights(bad_keys)


def test_anti_contamination_route_identifier():
    """Verify route identifiers cannot be mistakenly passed as lead-time classes."""
    bad_route_keys = {
        "DEL-BOM": Decimal("0.50"),
        "T+7": Decimal("0.50"),
    }
    with pytest.raises(ValueError, match="Route identifier"):
        validate_lead_time_weights(bad_route_keys)


def test_validation_rejects_invalid_lead_time_weights():
    """Verify validation rejects missing classes, negative weights, and wrong sums."""
    # Missing class
    with pytest.raises(ValueError, match="missing mandatory classes"):
        validate_lead_time_weights({"T+1": Decimal("0.5"), "T+7": Decimal("0.5")})

    # Negative weight
    with pytest.raises(ValueError, match="strictly positive"):
        validate_lead_time_weights({
            "T+1": Decimal("-0.05"),
            "T+7": Decimal("0.25"),
            "T+15": Decimal("0.20"),
            "T+21": Decimal("0.20"),
            "T+30": Decimal("0.20"),
            "T+45": Decimal("0.20"),
        })

    # Sum does not equal 1.0
    with pytest.raises(ValueError, match="must sum to 1.0000"):
        validate_lead_time_weights({
            "T+1": Decimal("0.10"),
            "T+7": Decimal("0.10"),
            "T+15": Decimal("0.10"),
            "T+21": Decimal("0.10"),
            "T+30": Decimal("0.10"),
            "T+45": Decimal("0.10"),
        })


def test_deterministic_weighted_aggregation_fixture():
    """
    Deterministic mathematical verification:
    Given identical elementary price index values across the 6 horizons:
      I(T+1)  = 100.00
      I(T+7)  = 110.00
      I(T+15) = 120.00
      I(T+21) = 130.00
      I(T+30) = 140.00
      I(T+45) = 150.00

    Empirical Weights:
      w(T+1)  = 0.0509  ->  5.0900
      w(T+7)  = 0.1350  -> 14.8500
      w(T+15) = 0.1491  -> 17.8920
      w(T+21) = 0.1519  -> 19.7470
      w(T+30) = 0.2588  -> 36.2320
      w(T+45) = 0.2543  -> 38.1450
      Sum = 131.9560

    Equal Weights (Sensitivity Analysis):
      Sum / 6 = 750 / 6 = 125.0000
    """
    # 1. Primary Empirical Aggregation
    reg_emp = WeightRegistry(lead_time_weight_mode="empirical")
    engine_emp = IndexAggregationEngine(weight_registry=reg_emp)

    lead_time_results = {
        ("DEL-BOM", "T+1"): LeadTimeIndexResult(
            route="DEL-BOM", lead_time_class="T+1", period="2026-09",
            index_value=Decimal("100.0000"), strata_count=1, weight=reg_emp.get_lead_time_weight("T+1"),
        ),
        ("DEL-BOM", "T+7"): LeadTimeIndexResult(
            route="DEL-BOM", lead_time_class="T+7", period="2026-09",
            index_value=Decimal("110.0000"), strata_count=1, weight=reg_emp.get_lead_time_weight("T+7"),
        ),
        ("DEL-BOM", "T+15"): LeadTimeIndexResult(
            route="DEL-BOM", lead_time_class="T+15", period="2026-09",
            index_value=Decimal("120.0000"), strata_count=1, weight=reg_emp.get_lead_time_weight("T+15"),
        ),
        ("DEL-BOM", "T+21"): LeadTimeIndexResult(
            route="DEL-BOM", lead_time_class="T+21", period="2026-09",
            index_value=Decimal("130.0000"), strata_count=1, weight=reg_emp.get_lead_time_weight("T+21"),
        ),
        ("DEL-BOM", "T+30"): LeadTimeIndexResult(
            route="DEL-BOM", lead_time_class="T+30", period="2026-09",
            index_value=Decimal("140.0000"), strata_count=1, weight=reg_emp.get_lead_time_weight("T+30"),
        ),
        ("DEL-BOM", "T+45"): LeadTimeIndexResult(
            route="DEL-BOM", lead_time_class="T+45", period="2026-09",
            index_value=Decimal("150.0000"), strata_count=1, weight=reg_emp.get_lead_time_weight("T+45"),
        ),
    }

    route_res_emp = engine_emp.aggregate_lead_time_to_route(lead_time_results, period="2026-09")
    del_bom_emp = route_res_emp["DEL-BOM"]

    # Verify exact analytical index value
    assert del_bom_emp.index_value == Decimal("131.9560")
    assert del_bom_emp.lead_time_weight_type == METHODOLOGY_STATUS_EMPIRICAL

    # 2. Sensitivity Analysis (Equal Weights)
    reg_eq = WeightRegistry(lead_time_weight_mode="sensitivity")
    engine_eq = IndexAggregationEngine(weight_registry=reg_eq)

    route_res_eq = engine_eq.aggregate_lead_time_to_route(lead_time_results, period="2026-09")
    del_bom_eq = route_res_eq["DEL-BOM"]

    assert del_bom_eq.index_value == Decimal("125.0000")
    assert del_bom_eq.lead_time_weight_type == METHODOLOGY_STATUS_SENSITIVITY


def test_apix_engine_metadata_and_separation():
    """Verify All-India APIx series result includes empirical lead-time metadata."""
    reg = WeightRegistry(is_single_route_pilot=False)
    assert reg.lead_time_weight_type == METHODOLOGY_STATUS_EMPIRICAL

    engine = IndexAggregationEngine(weight_registry=reg)

    route_results = {
        "DEL-BOM": RouteIndexResult(
            route="DEL-BOM",
            period="2026-09",
            index_value=Decimal("110.5000"),
            lead_times_included=["T+1", "T+7", "T+15", "T+21", "T+30", "T+45"],
            lead_time_weights=reg.lead_time_weights,
            lead_time_weight_type=reg.lead_time_weight_type,
        )
    }

    series = engine.aggregate_routes_to_apix(route_results, period="2026-09")

    # Lead-Time Metadata
    assert series.lead_time_weight_type == METHODOLOGY_STATUS_EMPIRICAL
    assert series.lead_time_weights_used["T+1"] == 0.0509
    assert series.lead_time_weights_used["T+21"] == 0.1519
    assert series.lead_time_weights_used["T+45"] == 0.2543

    # Route Basket Metadata (Top-60 CY2024) remains intact
    assert series.route_basket_id == "DGCA_CY2024_TOP60"
    assert series.route_basket_coverage_percent == Decimal("57.0247")

    # MoSPI CPI Weight Metadata remains intact and separate
    assert series.cpi_airfare_weight_percent == Decimal("0.02951")
    assert series.cpi_airfare_weight_decimal == Decimal("0.0002951")
