"""
Product Matching Engine for APIx Phase 3.
Matches comparable products across adjacent periods t-1 and t per Methodology §17 and §20.
"""

from __future__ import annotations
import math
from collections import defaultdict
from decimal import Decimal
from typing import Dict, List, Tuple
from .models import MonthlyProductPrice, MatchedProduct


class ProductMatchingEngine:
    """
    Identifies the matched set M_(s,t) of products present in both period t-1 and period t
    within each homogeneous stratum s.
    """

    def __init__(self, min_matched: int = 1, min_coverage: float = 0.50):
        self.min_matched = min_matched
        self.min_coverage = min_coverage

    def match_periods(
        self,
        prices_prev: Dict[str, MonthlyProductPrice],
        prices_curr: Dict[str, MonthlyProductPrice],
    ) -> Dict[str, Tuple[List[MatchedProduct], int, float, bool]]:
        """
        Matches products across two adjacent periods grouped by stratum_id.
        
        Returns:
            Dict mapping stratum_id -> (matched_products_list, eligible_count_prev, coverage_ratio, is_published)
        """
        # Map stratum_id -> dict of product_id -> MonthlyProductPrice for prev
        stratum_prev: Dict[str, Dict[str, MonthlyProductPrice]] = defaultdict(dict)
        for p in prices_prev.values():
            stratum_prev[p.stratum_id][p.product_id] = p

        # Map stratum_id -> dict of product_id -> MonthlyProductPrice for curr
        stratum_curr: Dict[str, Dict[str, MonthlyProductPrice]] = defaultdict(dict)
        for p in prices_curr.values():
            stratum_curr[p.stratum_id][p.product_id] = p

        matched_by_stratum: Dict[str, Tuple[List[MatchedProduct], int, float, bool]] = {}

        # All strata appearing in curr
        all_strata = set(stratum_curr.keys())

        for s_id in all_strata:
            curr_prods = stratum_curr.get(s_id, {})
            prev_prods = stratum_prev.get(s_id, {})
            eligible_prev = len(prev_prods)

            matched_list: List[MatchedProduct] = []

            for prod_id, curr_price in curr_prods.items():
                if prod_id in prev_prods:
                    prev_price = prev_prods[prod_id]
                    p0 = prev_price.geometric_price
                    pt = curr_price.geometric_price

                    if p0 > Decimal("0") and pt > Decimal("0"):
                        price_rel = pt / p0
                        log_rel = math.log(float(pt)) - math.log(float(p0))

                        matched_list.append(
                            MatchedProduct(
                                product_id=prod_id,
                                stratum_id=s_id,
                                p_prev=p0,
                                p_curr=pt,
                                price_relative=Decimal(str(round(price_rel, 6))),
                                log_price_relative=log_rel,
                            )
                        )

            matched_count = len(matched_list)
            coverage = (matched_count / eligible_prev) if eligible_prev > 0 else 0.0
            is_published = (matched_count >= self.min_matched) and (coverage >= self.min_coverage if eligible_prev > 0 else True)

            matched_by_stratum[s_id] = (matched_list, eligible_prev, coverage, is_published)

        return matched_by_stratum
