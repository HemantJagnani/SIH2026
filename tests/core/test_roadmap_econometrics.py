"""
Comprehensive Test Suite for APIx Mathematics and Econometrics Roadmap (§1 - §10).

Covers:
1. Longitudinal t1 Collection & Matching Engine
2. Full-Stratum Schedule-Churn Imputation (Class-Mean Fallback)
3. Dynamic Hedonic Quality Adjustment (Log-Linear Ridge Regression)
4. Continuous Multi-Day Monthly Collection & Active-Day Qualification
5. Elementary & Higher-Level Uncertainty / Variance Propagation (Delta Method)
6. Mandatory Checkout Fee Harmonization & Non-Fabrication
7. Annual December Chain-Linking Engine
8. Analytical Seasonal Adjustment Pipeline & Moving Holiday Interface
9. Urban/Rural Sectoral CPI Contribution Integration
10. Annual DGCA Route-Weight Update Framework & Churn Tracking

Strict Governance Invariants:
- Zero fabrication of observations, weights, fees, coefficients, or standard errors.
- P_ref (₹8,641.45) is descriptive only; never enters index denominator.
- Headline APIx remains unadjusted; analytical pipelines are segregated.
- Unfilled future longitudinal or external datasets remain strictly DATA_DEPENDENT_INACTIVE.
"""

from __future__ import annotations
from datetime import date, datetime, timezone
from decimal import Decimal
import math
import pytest
from uuid import uuid4

# Import all roadmap modules directly from index package
from index.longitudinal import (
    LongitudinalCollectionWorkflow,
    LongitudinalMatchingEngine,
    LongitudinalTargetCell,
    LongitudinalMatchingResult,
)
from index.quality_adjustment import (
    ClassMeanImputationEngine,
    ImputedClassMeanResult,
    ImputationStatus,
)
from index.hedonic import (
    HedonicRegressionEngine,
    HedonicModelStatus,
    HedonicAdjustmentResult,
)
from index.monthly_aggregation import (
    MonthlyAggregationEngine,
    MonthlyAggregatedProduct,
)
from index.uncertainty import (
    UncertaintyEstimationEngine,
    UncertaintyMetrics,
)
from index.checkout import (
    CheckoutHarmonizationEngine,
    CheckoutVerificationStatus,
    HarmonizedCheckoutPrice,
)
from index.chain_linking import (
    AnnualChainLinkingEngine,
    AnnualChainSeries,
    AnnualLinkRecord,
)
from index.seasonal_adjustment import (
    SeasonalAdjustmentEngine,
    SeasonalAdjustmentResult,
)
from index.cpi_contribution import (
    CPIContributionEngine,
    SectoralCPIContribution,
)
from index.dgca_weights import (
    DGCARouteWeightRegistry,
    AnnualRouteBasket,
    RouteTransitionStatus,
)
from index.models import MonthlyProductPrice, MatchedProduct
from index.route_basket import get_top60_route_weights


# ============================================================================
# 1. LONGITUDINAL t1 COLLECTION SUPPORT (§Roadmap Item 1)
# ============================================================================

def test_longitudinal_target_cell_planning_360_cells():
    """Workflow must generate exactly 360 cells preserving collection_period != travel_date."""
    top60 = list(get_top60_route_weights(use_iata_codes=True).keys())
    assert len(top60) == 60

    workflow = LongitudinalCollectionWorkflow(routes=top60)
    targets = workflow.generate_360_cell_target_plan(
        collection_date=date(2026, 10, 1),
        collection_period="2026-10",
    )
    assert len(targets) == 360

    # Verify every cell maintains collection_period separate from travel_date
    for t in targets:
        assert t.collection_period == "2026-10"
        assert t.target_travel_date > date(2026, 10, 1)
        assert t.lead_days in (1, 7, 15, 21, 30, 45)


def test_longitudinal_matching_and_refusal_when_unmatched():
    """Matches products across t0 and t1; refuses index if no comparable pairs exist."""
    engine = LongitudinalMatchingEngine()

    p0 = MonthlyProductPrice(
        product_id="FP_DELBOM_6E501",
        stratum_id="STRAT_1",
        route="DEL-BOM",
        lead_time_class="T+15",
        month="2026-09",
        active_days=5,
        geometric_price=Decimal("6000.00"),
        observation_count=5,
        quality_status="VALID",
    )
    p1 = MonthlyProductPrice(
        product_id="FP_DELBOM_6E501",
        stratum_id="STRAT_1",
        route="DEL-BOM",
        lead_time_class="T+15",
        month="2026-10",
        active_days=5,
        geometric_price=Decimal("6600.00"),
        observation_count=5,
        quality_status="VALID",
    )

    # Case A: Matching product in t0 and t1
    res_matched = engine.match_longitudinal_periods(
        prices_t0={"FP_DELBOM_6E501": p0},
        prices_t1={"FP_DELBOM_6E501": p1},
        period_t0_label="2026-09",
        period_t1_label="2026-10",
    )
    assert res_matched.can_calculate_monthly_index is True
    assert res_matched.status == "LONGITUDINAL_MATCH_READY"
    assert res_matched.total_matched_product_pairs == 1
    m = res_matched.matched_products_by_stratum["STRAT_1"][0]
    assert m.price_relative == Decimal("1.100000")  # 6600 / 6000

    # Case B: Completely non-overlapping products (refusal to calculate index)
    p1_diff = MonthlyProductPrice(
        product_id="FP_DELBOM_AI802",
        stratum_id="STRAT_2",
        route="DEL-BOM",
        lead_time_class="T+15",
        month="2026-10",
        active_days=5,
        geometric_price=Decimal("7000.00"),
        observation_count=5,
        quality_status="VALID",
    )
    res_unmatched = engine.match_longitudinal_periods(
        prices_t0={"FP_DELBOM_6E501": p0},
        prices_t1={"FP_DELBOM_AI802": p1_diff},
        period_t0_label="2026-09",
        period_t1_label="2026-10",
    )
    assert res_unmatched.can_calculate_monthly_index is False
    assert res_unmatched.status == "NO_COMPARABLE_PRODUCTS"
    assert res_unmatched.total_matched_product_pairs == 0


# ============================================================================
# 2. FULL-STRATUM SCHEDULE-CHURN IMPUTATION (§Roadmap Item 2)
# ============================================================================

def test_full_stratum_imputation_fallback_hierarchy():
    """Verifies 3-tier parent hierarchy fallback when a homogeneous stratum churns."""
    engine = ClassMeanImputationEngine()

    m1 = MatchedProduct(
        product_id="P1",
        stratum_id="S_DONOR1",
        p_prev=Decimal("5000.00"),
        p_curr=Decimal("5500.00"),
        price_relative=Decimal("1.100000"),
        log_price_relative=math.log(1.10),
    )
    matched_dict = {
        "S_DONOR1": ([m1], 1, 1.0, True),
    }
    meta = {
        "S_DONOR1": {"route": "DEL-BOM", "lead_time_class": "T+15", "airline": "6E"},
    }

    # Missing stratum S_TARGET has 100% attrition:
    res = engine.impute_stratum_link(
        stratum_id="S_TARGET",
        route="DEL-BOM",
        lead_time_class="T+15",
        period="2026-10",
        matched_by_stratum=matched_dict,
        stratum_metadata=meta,
        airline="6E",
    )
    assert res.is_imputed is True
    assert res.status == ImputationStatus.IMPUTED_CLASS_MEAN
    assert res.donor_hierarchy_level == "ROUTE_CARRIER_LEADTIME"
    assert res.imputed_jevons_link == Decimal("1.100000")


def test_full_stratum_100_percent_attrition_never_imputes_zero():
    """If 0 donors exist anywhere, returns UNIMPUTABLE_NO_DONORS with None, NEVER zero."""
    engine = ClassMeanImputationEngine()
    res = engine.impute_stratum_link(
        stratum_id="S_EMPTY",
        route="DEL-GAU",
        lead_time_class="T+30",
        period="2026-10",
        matched_by_stratum={},  # Zero donors
        stratum_metadata={},
        airline="6E",
    )
    assert res.status == ImputationStatus.UNIMPUTABLE_NO_DONORS
    assert res.imputed_jevons_link is None  # Preserves None/Null; NEVER zero!


# ============================================================================
# 3. DYNAMIC HEDONIC QUALITY ADJUSTMENT (§Roadmap Item 3)
# ============================================================================

class DummyHedonicObs:
    def __init__(self, fare: float, lead: int = 7, bag: int = 15, stops: int = 0, airline: str = "6E"):
        self.total_fare = Decimal(str(fare))
        self.duration_minutes = 120
        self.baggage_allowance_kg = bag
        self.lead_days = lead
        self.airline = airline
        self.departure_time_band = "MORNING"
        self.stops = stops
        self.fare_family = "REGULAR_FARE"
        self.travel_day_type = "WEEKDAY"
        self.quality_status = "VALID"


def test_hedonic_non_fabrication_safeguard_below_sample_threshold():
    """Hedonic engine must remain DATA_DEPENDENT_INACTIVE when sample size < 30; never fabricate."""
    engine = HedonicRegressionEngine(min_sample_size=30)
    small_obs = [DummyHedonicObs(5000 + i * 100) for i in range(5)]
    st = engine.fit(small_obs)
    assert st == HedonicModelStatus.INSUFFICIENT_SAMPLE_SIZE
    assert engine.status == HedonicModelStatus.INSUFFICIENT_SAMPLE_SIZE

    # Quality adjustment falls back to deterministic rule
    base = DummyHedonicObs(5000, bag=15)
    cand = DummyHedonicObs(5500, bag=20)  # +5kg baggage
    adj = engine.evaluate_quality_adjustment(base, cand, Decimal("5500.00"))
    assert adj.is_fallback is True
    assert adj.valuation_method == "DETERMINISTIC_BENCHMARK_FALLBACK"
    assert adj.net_quality_adjustment_inr == Decimal("500.00")
    assert adj.adjusted_price_inr == Decimal("5000.00")


def test_hedonic_ridge_regularization_and_backtest():
    """Hedonic engine fits log-linear model with Ridge regularization when N >= 30."""
    engine = HedonicRegressionEngine(min_sample_size=30, l2_penalty=0.1)
    training_obs = []
    for i in range(40):
        lead = 1 + (i % 45)
        bag = 15 if i % 2 == 0 else 20
        stops = 0 if i % 3 != 0 else 1
        carrier = "6E" if i % 2 == 0 else "AI"
        fare = 4000.0 + (i * 50) + (bag * 20)
        training_obs.append(DummyHedonicObs(fare, lead=lead, bag=bag, stops=stops, airline=carrier))

    st = engine.fit(training_obs)
    assert st == HedonicModelStatus.CALIBRATED_ACTIVE
    assert len(engine.coefficients) > 0
    assert engine.diagnostics is not None
    assert engine.diagnostics.sample_size == 40

    # Backtesting hook
    bt = engine.backtest(training_obs[:10])
    assert bt["sample_size"] == 10.0
    assert "rmse" in bt
    assert "mae" in bt


# ============================================================================
# 4. CONTINUOUS MULTI-DAY MONTHLY COLLECTION (§Roadmap Item 4)
# ============================================================================

class DummyDailyObs:
    def __init__(self, key: str, fare: float, coll_date: date):
        self.product_key = key
        self.total_fare = Decimal(str(fare))
        self.collection_date = coll_date
        self.travel_date = date(2026, 10, 15)
        self.quality_status = "VALID"
        self.product_stratum_id = "STRAT_1"
        self.route = "DEL-BOM"
        self.lead_time_class = "T+15"


def test_monthly_aggregation_active_day_qualification():
    """Computes intra-month geometric mean with configurable 0.30 active-day qualification."""
    engine = MonthlyAggregationEngine(active_days_threshold=0.30)

    # Good product: observed on 12 distinct dates in 30-day month (12/30 = 0.40 >= 0.30)
    good_obs = [DummyDailyObs("P_GOOD", 5000 + d * 20, date(2026, 9, d)) for d in range(1, 13)]
    # Sparse product: observed on 3 distinct dates (3/30 = 0.10 < 0.30)
    sparse_obs = [DummyDailyObs("P_SPARSE", 6000, date(2026, 9, d)) for d in range(1, 4)]

    res = engine.aggregate_monthly_observations(good_obs + sparse_obs, "2026-09", total_calendar_days=30)
    assert len(res) == 2

    assert res["P_GOOD"].qualifies_for_headline is True
    assert res["P_GOOD"].qualification_status == "QUALIFIED_HEADLINE"
    assert res["P_GOOD"].active_days_ratio == 0.40
    assert res["P_GOOD"].geometric_price > Decimal("5000.00")

    assert res["P_SPARSE"].qualifies_for_headline is False
    assert res["P_SPARSE"].qualification_status == "BELOW_ACTIVE_DAYS_THRESHOLD"
    assert res["P_SPARSE"].active_days_ratio == 0.10
    assert res["P_SPARSE"].geometric_price == Decimal("6000.00")


# ============================================================================
# 5. VARIANCE / STANDARD ERRORS / 95% CI (§Roadmap Item 5)
# ============================================================================

class DummyMatchedPair:
    def __init__(self, log_rel: float):
        self.log_price_relative = log_rel


def test_uncertainty_elementary_variance_and_delta_method():
    """Computes Jevons log variance, Delta method standard errors, and 95% CIs."""
    engine = UncertaintyEstimationEngine()

    matched = [
        DummyMatchedPair(math.log(1.02)),
        DummyMatchedPair(math.log(1.05)),
        DummyMatchedPair(math.log(1.08)),
        DummyMatchedPair(math.log(1.10)),
    ]
    metrics = engine.compute_elementary_uncertainty(matched, Decimal("106.18"), stratum_id="S1")
    assert metrics.status == "AVAILABLE"
    assert metrics.sample_size == 4
    assert metrics.variance is not None and metrics.variance > 0
    assert metrics.standard_error is not None and metrics.standard_error > 0
    assert metrics.ci95_lower is not None and metrics.ci95_upper is not None
    assert metrics.ci95_lower < 106.18 < metrics.ci95_upper


def test_uncertainty_never_manufactures_ci_for_small_n():
    """Returns NOT_AVAILABLE when N < 2; never fabricates confidence intervals."""
    engine = UncertaintyEstimationEngine()
    # 1 matched product
    metrics_single = engine.compute_elementary_uncertainty([DummyMatchedPair(math.log(1.05))], Decimal("105.00"), stratum_id="S1")
    assert metrics_single.status == "NOT_AVAILABLE"
    assert metrics_single.variance is None
    assert metrics_single.standard_error is None
    assert metrics_single.ci95_lower is None
    assert metrics_single.ci95_upper is None

    # 0 matched products
    metrics_empty = engine.compute_elementary_uncertainty([], Decimal("100.00"), stratum_id="S1")
    assert metrics_empty.status == "NOT_AVAILABLE"


# ============================================================================
# 6. MANDATORY CHECKOUT FEE HARMONIZATION (§Roadmap Item 6)
# ============================================================================

def test_checkout_fee_harmonization_and_optional_fee_exclusion():
    """Distinguishes mandatory fees, discounts, and strictly excludes optional charges."""
    engine = CheckoutHarmonizationEngine()
    harmonized = engine.reconcile_checkout_price(
        search_card_price=Decimal("5200.00"),
        mandatory_checkout_fee=Decimal("586.00"),
        unconditional_discount=Decimal("100.00"),
        raw_optional_charges={"MEAL": Decimal("350.00"), "SEAT": Decimal("400.00")},
        source="google_flights",
    )
    assert harmonized.verification_status == CheckoutVerificationStatus.VERIFIED_CHECKOUT
    assert harmonized.search_card_price == Decimal("5200.00")
    assert harmonized.mandatory_checkout_fee == Decimal("586.00")
    assert harmonized.unconditional_discount == Decimal("100.00")
    assert harmonized.final_mandatory_payable_price == Decimal("5686.00")
    assert "MEAL" in harmonized.optional_charges_excluded
    assert "SEAT" in harmonized.optional_charges_excluded


def test_checkout_unverified_retains_card_fare_without_inventing_fees():
    """If checkout cannot be verified, does NOT invent fee; retains search card price."""
    engine = CheckoutHarmonizationEngine()
    harmonized = engine.reconcile_checkout_price(
        search_card_price=Decimal("6400.00"),
        mandatory_checkout_fee=None,  # Unverified
        source="google_flights",
    )
    assert harmonized.verification_status == CheckoutVerificationStatus.UNVERIFIED_LISTING_FARE_RETAINED
    assert harmonized.mandatory_checkout_fee is None
    assert harmonized.final_mandatory_payable_price == Decimal("6400.00")


# ============================================================================
# 7. ANNUAL DECEMBER CHAIN-LINKING (§Roadmap Item 7)
# ============================================================================

def test_annual_december_chain_linking_formula():
    """Links annual baskets at December without overwriting published historical series."""
    engine = AnnualChainLinkingEngine(base_year="2024=100")
    assert engine.status == "DATA_DEPENDENT_INACTIVE"

    # Register Dec 2024 index value = 106.00
    rec = engine.register_december_link(year=2024, december_index_value=Decimal("106.00"), weights_version="CY2024_v1")
    assert engine.status == "ACTIVE"
    assert rec.chain_link_factor == Decimal("1.060000")

    # In Jan 2025, new basket index is 102.00
    linked_val = engine.chain_monthly_index("2025-01", Decimal("102.00"))
    # Linked index = 1.06 * 102.00 = 108.12
    assert linked_val == Decimal("108.1200")


def test_annual_chain_linking_inactive_without_link_period():
    """Remains direct if preceding year December link does not exist."""
    engine = AnnualChainLinkingEngine(base_year="2024=100")
    val = engine.chain_monthly_index("2024-06", Decimal("103.50"))
    assert val == Decimal("103.50")


# ============================================================================
# 8. SEASONAL ADJUSTMENT MODULE (§Roadmap Item 8)
# ============================================================================

def test_seasonal_adjustment_guards_and_analytical_label():
    """Enforces >= 36 months requirement and marks output as SEASONALLY_ADJUSTED_ANALYTICAL."""
    engine = SeasonalAdjustmentEngine(min_series_length=36)
    short_series = {f"2024-{m:02d}": Decimal("100.00") + Decimal(str(m)) for m in range(1, 13)}
    res_short = engine.adjust_series(short_series, target_period="2024-06")
    assert res_short.status == "NOT_AVAILABLE"
    assert res_short.seasonally_adjusted_apix is None
    assert "Insufficient historical time series" in res_short.reason

    # Long series (36 months)
    long_series = {}
    for y in [2022, 2023, 2024]:
        for m in range(1, 13):
            long_series[f"{y}-{m:02d}"] = Decimal("100.00") + Decimal(str((m % 6) * 2))
    res_long = engine.adjust_series(long_series, target_period="2023-06")
    assert res_long.status == "SEASONALLY_ADJUSTED_ANALYTICAL"
    assert res_long.seasonally_adjusted_apix is not None
    assert res_long.headline_unadjusted_apix == Decimal("100.00")


# ============================================================================
# 9. URBAN/RURAL CPI CONTRIBUTION OUTPUT (§Roadmap Item 9)
# ============================================================================

def test_urban_rural_cpi_contribution_calculations():
    """Verifies combined (0.02951%), urban (0.017843%), and rural (0.011666%) contributions."""
    engine = CPIContributionEngine()
    contrib = engine.calculate_sectoral_contributions(Decimal("10.00"), period="2026-09")
    assert contrib.cpi_combined_contribution_pp == Decimal("0.00295100")
    assert contrib.cpi_urban_contribution_pp == Decimal("0.00178430")
    assert contrib.cpi_rural_contribution_pp == Decimal("0.00116660")
    # Sub-sector weights sum with small rounding per official MoSPI publication
    assert abs((contrib.cpi_airfare_weight_urban_percent + contrib.cpi_airfare_weight_rural_percent) - contrib.cpi_airfare_weight_combined_percent) < Decimal("0.00001")


# ============================================================================
# 10. DGCA ANNUAL ROUTE-WEIGHT UPDATE FRAMEWORK (§Roadmap Item 10)
# ============================================================================

def test_dgca_annual_route_weights_registry_and_transitions():
    """CY2024 Top-60 is immutable with sum(W)=1.000000; detects route churn for future years."""
    registry = DGCARouteWeightRegistry()
    basket_2024 = registry.get_basket("CY2024")
    assert basket_2024.status == "ACTIVE_PRODUCTION"
    assert basket_2024.route_count == 60
    assert abs(sum(basket_2024.weights.values()) - Decimal("1.000000")) < Decimal("0.000001")

    # Ingest hypothetical CY2025 traffic
    prev_routes = list(basket_2024.weights.keys())
    hypo_pax = {r: 100000 for r in prev_routes[:-1]}
    hypo_pax["IXR-DEL"] = 250000  # New entrant
    basket_2025 = registry.register_annual_traffic_report(
        year_label="CY2025",
        city_pair_passenger_volumes=hypo_pax,
        total_national_passengers=150000000,
        published_date="2025-03-31",
        provenance_reference="DGCA CY2025 Provisional Report",
        activate_immediately=False,
    )
    assert basket_2025.status == "PENDING_OFFICIAL_DGCA_PUBLICATION"
    assert basket_2025.route_count == 60
    assert abs(sum(basket_2025.weights.values()) - Decimal("1.000000")) < Decimal("0.000001")
    transitions = {t.route: t.transition_status for t in basket_2025.transitions}
    assert transitions["IXR-DEL"] == RouteTransitionStatus.NEW_ENTRANT
    assert transitions[prev_routes[-1]] == RouteTransitionStatus.EXIT
