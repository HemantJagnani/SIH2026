"""
Index Aggregation Engine for APIx Phase 3.
Implements lead-time aggregation, route aggregation, and All-India APIx compilation
per Methodology §21, §22, §28, §29.
"""

from __future__ import annotations
from collections import defaultdict
from decimal import Decimal
from typing import Dict, List, Optional
from .models import (
    ElementaryIndexResult,
    LeadTimeIndexResult,
    RouteIndexResult,
    APIxSeriesResult,
)
from .weights import WeightRegistry


class IndexAggregationEngine:
    """
    Higher-level Young/Modified Laspeyres weighted aggregation engine.
    Aggregates:
        Elementary Strata -> Lead-Time Index I_(r,l,t)
        Lead-Time Indices -> Route Index I_(r,t)
        Route Indices     -> All-India APIx_t
    """

    def __init__(self, weight_registry: Optional[WeightRegistry] = None):
        self.weights = weight_registry or WeightRegistry()

    def aggregate_elementary_to_lead_time(
        self,
        elementary_results: List[ElementaryIndexResult],
        period: str,
    ) -> Dict[tuple[str, str], LeadTimeIndexResult]:
        """
        Aggregates elementary strata within (route, lead_time_class):
            I_(r,l,t) = mean over strata q of I_(r,l,q,t)
        Returns:
            Dict mapping (route, lead_time_class) -> LeadTimeIndexResult
        """
        grouped: Dict[tuple[str, str], list[ElementaryIndexResult]] = defaultdict(list)
        for el in elementary_results:
            if el.is_published and el.period == period:
                grouped[(el.route, el.lead_time_class)].append(el)

        lead_time_results: Dict[tuple[str, str], LeadTimeIndexResult] = {}
        for (route, lead_time), el_list in grouped.items():
            if not el_list:
                continue
            # Arithmetic average across homogeneous product strata within lead-time class
            avg_index = sum(e.chained_index for e in el_list) / Decimal(str(len(el_list)))
            lead_time_results[(route, lead_time)] = LeadTimeIndexResult(
                route=route,
                lead_time_class=lead_time,
                period=period,
                index_value=Decimal(str(round(avg_index, 4))),
                strata_count=len(el_list),
            )

        return lead_time_results

    def aggregate_lead_time_to_route(
        self,
        lead_time_results: Dict[tuple[str, str], LeadTimeIndexResult],
        period: str,
    ) -> Dict[str, RouteIndexResult]:
        """
        Aggregates lead-time indices into route-level index:
            I_(r,t) = sum_l W_l * I_(r,l,t)
        """
        # Group by route
        by_route: Dict[str, Dict[str, Decimal]] = defaultdict(dict)
        for (route, lead_time), res in lead_time_results.items():
            if res.period == period:
                by_route[route][lead_time] = res.index_value

        route_results: Dict[str, RouteIndexResult] = {}
        for route, lt_dict in by_route.items():
            if not lt_dict:
                continue
            available_lts = list(lt_dict.keys())
            cond_weights = self.weights.get_normalized_sub_weights(
                available_lts, self.weights.lead_time_weights
            )
            route_index = sum(cond_weights[lt] * lt_dict[lt] for lt in available_lts)
            route_results[route] = RouteIndexResult(
                route=route,
                period=period,
                index_value=Decimal(str(round(route_index, 4))),
                lead_times_included=sorted(available_lts),
            )

        return route_results

    def aggregate_routes_to_apix(
        self,
        route_results: Dict[str, RouteIndexResult],
        period: str,
        prev_apix_val: Optional[Decimal] = None,
        year_ago_apix_val: Optional[Decimal] = None,
    ) -> APIxSeriesResult:
        """
        Aggregates route indices into All-India APIx:
            APIx_t = sum_r W_r * I_(r,t)
        Computes MoM and YoY growth rates.
        """
        if not route_results:
            # Baseline neutral index
            return APIxSeriesResult(
                period=period,
                index_value=Decimal("100.00"),
                mom_percent=Decimal("0.00"),
                yoy_percent=Decimal("0.00"),
                weight_version=self.weights.version,
            )

        available_routes = list(route_results.keys())
        cond_weights = self.weights.get_normalized_sub_weights(
            available_routes, self.weights.route_weights
        )

        final_index = sum(
            cond_weights[r] * route_results[r].index_value for r in available_routes
        )
        final_index_dec = Decimal(str(round(final_index, 4)))

        # Month-on-Month inflation
        mom = None
        if prev_apix_val and prev_apix_val > Decimal("0"):
            mom = ((final_index_dec / prev_apix_val) - Decimal("1.0")) * Decimal("100.0")
            mom = Decimal(str(round(mom, 2)))

        # Year-on-Year inflation
        yoy = None
        if year_ago_apix_val and year_ago_apix_val > Decimal("0"):
            yoy = ((final_index_dec / year_ago_apix_val) - Decimal("1.0")) * Decimal("100.0")
            yoy = Decimal(str(round(yoy, 2)))

        return APIxSeriesResult(
            index_name="India Airfare Price Index",
            period=period,
            index_value=final_index_dec,
            mom_percent=mom,
            yoy_percent=yoy,
            route_indices={r: res.index_value for r, res in route_results.items()},
            weight_version=self.weights.version,
        )
