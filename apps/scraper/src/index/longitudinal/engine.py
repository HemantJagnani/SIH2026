"""
Longitudinal Collection Workflow & Cross-Period Matching Engine (§Roadmap Item 1).

Conforms to:
- Distinct tracking of collection_period and travel_date.
- Matching identical homogeneous product keys across period t0 and period t1.
- Strict refusal to calculate monthly index unless comparable longitudinal observations exist.
"""

from __future__ import annotations
import math
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Sequence, Tuple

from index.models import MonthlyProductPrice, MatchedProduct
from .models import LongitudinalTargetCell, LongitudinalMatchingResult


class LongitudinalCollectionWorkflow:
    """
    Orchestrates the target matrix configuration for the second-period (t1) collection
    across all 360 (route x lead-time) cells.
    """

    LEAD_TIME_DAYS_MAP = {
        "T+1": 1,
        "T+7": 7,
        "T+15": 15,
        "T+21": 21,
        "T+30": 30,
        "T+45": 45,
    }

    def __init__(self, routes: Sequence[str]):
        self.routes = list(routes)

    def generate_360_cell_target_plan(
        self,
        collection_date: date,
        collection_period: str,
    ) -> List[LongitudinalTargetCell]:
        """
        Generates the target list of all 360 cells for period t1.
        Preserves collection_date and collection_period separately from travel_date.
        """
        plan: List[LongitudinalTargetCell] = []
        for route in sorted(self.routes):
            for lt_class, lead_days in sorted(self.LEAD_TIME_DAYS_MAP.items(), key=lambda x: x[1]):
                target_travel = collection_date + timedelta(days=lead_days)
                plan.append(
                    LongitudinalTargetCell(
                        route=route,
                        lead_time_class=lt_class,
                        lead_days=lead_days,
                        target_travel_date=target_travel,
                        collection_period=collection_period,
                        status="SCHEDULED_FOR_COLLECTION",
                    )
                )
        return plan


class LongitudinalMatchingEngine:
    """
    Matches representative product prices across period t0 and period t1.
    Computes price relatives strictly for genuinely comparable products:
        r_(i,t) = P_(i,t) / P_(i,t-1)
    """

    def __init__(self, min_matched_per_stratum: int = 1, min_coverage: float = 0.50):
        self.min_matched = min_matched_per_stratum
        self.min_coverage = min_coverage

    def match_longitudinal_periods(
        self,
        prices_t0: Dict[str, MonthlyProductPrice],
        prices_t1: Dict[str, MonthlyProductPrice],
        period_t0_label: str,
        period_t1_label: str,
        collection_timestamp_t0: Optional[str] = None,
        collection_timestamp_t1: Optional[str] = None,
    ) -> LongitudinalMatchingResult:
        """
        Evaluates cross-period product overlap.
        Preserves collection timestamps separately from travel dates.
        """
        # Group by stratum_id -> product_id -> MonthlyProductPrice
        strata_t0: Dict[str, Dict[str, MonthlyProductPrice]] = defaultdict(dict)
        for p in prices_t0.values():
            if p.quality_status == "VALID" and p.geometric_price > Decimal("0"):
                strata_t0[p.stratum_id][p.product_id] = p

        strata_t1: Dict[str, Dict[str, MonthlyProductPrice]] = defaultdict(dict)
        for p in prices_t1.values():
            if p.quality_status == "VALID" and p.geometric_price > Decimal("0"):
                strata_t1[p.stratum_id][p.product_id] = p

        all_strata = sorted(set(strata_t0.keys()).union(set(strata_t1.keys())))
        matched_by_stratum: Dict[str, List[MatchedProduct]] = {}
        total_matched_pairs = 0
        matched_strata_count = 0
        unmatched_strata_count = 0

        for s_id in all_strata:
            t0_prods = strata_t0.get(s_id, {})
            t1_prods = strata_t1.get(s_id, {})
            common_keys = set(t0_prods.keys()).intersection(set(t1_prods.keys()))

            stratum_matches: List[MatchedProduct] = []
            for prod_id in sorted(common_keys):
                p0 = t0_prods[prod_id].geometric_price
                pt = t1_prods[prod_id].geometric_price
                if p0 > Decimal("0") and pt > Decimal("0"):
                    rel = pt / p0
                    log_rel = math.log(float(pt)) - math.log(float(p0))
                    stratum_matches.append(
                        MatchedProduct(
                            product_id=prod_id,
                            stratum_id=s_id,
                            p_prev=p0,
                            p_curr=pt,
                            price_relative=Decimal(str(round(rel, 6))),
                            log_price_relative=log_rel,
                        )
                    )

            if stratum_matches:
                matched_by_stratum[s_id] = stratum_matches
                total_matched_pairs += len(stratum_matches)
                matched_strata_count += 1
            else:
                unmatched_strata_count += 1

        total_eligible_t0 = sum(len(prods) for prods in strata_t0.values())
        total_eligible_t1 = sum(len(prods) for prods in strata_t1.values())
        coverage = (total_matched_pairs / total_eligible_t0) if total_eligible_t0 > 0 else 0.0

        can_calc = total_matched_pairs > 0 and period_t0_label != period_t1_label
        if total_matched_pairs == 0:
            status = "NO_COMPARABLE_PRODUCTS"
        elif coverage < self.min_coverage:
            status = "INSUFFICIENT_LONGITUDINAL_DATA"
        else:
            status = "LONGITUDINAL_MATCH_READY"

        return LongitudinalMatchingResult(
            period_t0=period_t0_label,
            period_t1=period_t1_label,
            collection_timestamp_t0=collection_timestamp_t0,
            collection_timestamp_t1=collection_timestamp_t1,
            total_strata_evaluated=len(all_strata),
            matched_strata_count=matched_strata_count,
            unmatched_strata_count=unmatched_strata_count,
            total_matched_product_pairs=total_matched_pairs,
            matched_products_by_stratum=matched_by_stratum,
            eligible_products_t0_count=total_eligible_t0,
            eligible_products_t1_count=total_eligible_t1,
            longitudinal_coverage_ratio=round(coverage, 4),
            status=status,
            can_calculate_monthly_index=can_calc,
        )
