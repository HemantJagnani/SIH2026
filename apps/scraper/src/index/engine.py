"""
APIx Master Index Compilation Engine for Phase 3.
Orchestrates the complete calculation hierarchy:
Monthly Product Pricing -> Matching Engine -> Short-Chain Jevons -> Lead-Time Aggregation -> Route Aggregation -> APIx.
"""

from __future__ import annotations
from decimal import Decimal
from typing import Dict, List, Optional, Sequence
from models.canonical import NormalizedFareObservation
from .models import (
    MonthlyProductPrice,
    ElementaryIndexResult,
    LeadTimeIndexResult,
    RouteIndexResult,
    APIxSeriesResult,
)
from .monthly_pricing import compute_monthly_product_prices
from .matching import ProductMatchingEngine
from .jevons import JevonsEngine
from .weights import WeightRegistry
from .aggregation import IndexAggregationEngine


class APIxEngine:
    """
    Production index calculation engine conforming to MoSPI CPI 2024 and Eurostat HICP standards.
    """

    def __init__(
        self,
        weight_registry: Optional[WeightRegistry] = None,
        min_matched: int = 1,
        min_coverage: float = 0.50,
        base_value: Decimal = Decimal("100.00"),
    ):
        self.weights = weight_registry or WeightRegistry()
        self.matching_engine = ProductMatchingEngine(
            min_matched=min_matched, min_coverage=min_coverage
        )
        self.jevons_engine = JevonsEngine(base_value=base_value)
        self.aggregation_engine = IndexAggregationEngine(weight_registry=self.weights)
        
        # State stores
        self.monthly_prices_by_period: Dict[str, Dict[str, MonthlyProductPrice]] = {}
        self.apix_history: Dict[str, APIxSeriesResult] = {}

    def process_period(
        self,
        period: str,
        observations: Sequence[NormalizedFareObservation],
        prev_period: Optional[str] = None,
    ) -> APIxSeriesResult:
        """
        Executes full calculation hierarchy for a given month period (YYYY-MM):
        1. Calculate monthly geometric product prices P̄_(i,t)
        2. Match products M_(s,t) against prev_period
        3. Compute short-chain Jevons elementary links and chained indices
        4. Aggregate across lead times using booking weights W_l
        5. Aggregate across routes using route weights W_r
        6. Return complete APIxSeriesResult with audit metadata
        """
        # 1. Compute monthly geometric product prices
        monthly_prices = compute_monthly_product_prices(observations)
        self.monthly_prices_by_period[period] = monthly_prices

        # If base period or no previous period provided, initialize reference
        if not prev_period or prev_period not in self.monthly_prices_by_period:
            # Baseline period: Jevons links = 1.0, chained = 100.0
            elementary_results: List[ElementaryIndexResult] = []
            for p in monthly_prices.values():
                el = self.jevons_engine.compute_elementary_index(
                    stratum_id=p.stratum_id,
                    route=p.route,
                    lead_time_class=p.lead_time_class,
                    period=period,
                    prev_period=None,
                    matched_products=[],
                    eligible_count_prev=0,
                    coverage_ratio=1.0,
                    is_published=True,
                )
                elementary_results.append(el)
        else:
            # 2. Match products across adjacent periods
            prev_prices = self.monthly_prices_by_period[prev_period]
            matches = self.matching_engine.match_periods(prev_prices, monthly_prices)

            # 3. Compute Jevons elementary index for each stratum
            elementary_results = []
            # Extract sample metadata (route, lead_time) from current prices
            stratum_metadata: Dict[str, tuple[str, str]] = {}
            for p in monthly_prices.values():
                stratum_metadata[p.stratum_id] = (p.route, p.lead_time_class)

            for s_id, (matched_list, elig_prev, coverage, is_pub) in matches.items():
                route, lead_time = stratum_metadata.get(s_id, ("UNKNOWN", "T+7"))
                el = self.jevons_engine.compute_elementary_index(
                    stratum_id=s_id,
                    route=route,
                    lead_time_class=lead_time,
                    period=period,
                    prev_period=prev_period,
                    matched_products=matched_list,
                    eligible_count_prev=elig_prev,
                    coverage_ratio=coverage,
                    is_published=is_pub,
                )
                elementary_results.append(el)

        # 4. Aggregate elementary strata to lead-time indices
        lt_results = self.aggregation_engine.aggregate_elementary_to_lead_time(
            elementary_results, period
        )

        # 5. Aggregate lead-time indices to route indices
        route_results = self.aggregation_engine.aggregate_lead_time_to_route(
            lt_results, period
        )

        # 6. Aggregate routes to final All-India APIx
        prev_apix_val = None
        if prev_period and prev_period in self.apix_history:
            prev_apix_val = self.apix_history[prev_period].index_value

        apix_res = self.aggregation_engine.aggregate_routes_to_apix(
            route_results=route_results,
            period=period,
            prev_apix_val=prev_apix_val,
        )

        # Populate lead-time sub-indices in the final result
        apix_res.lead_time_indices = {
            f"{k[0]}_{k[1]}": v.index_value for k, v in lt_results.items()
        }

        self.apix_history[period] = apix_res
        return apix_res
