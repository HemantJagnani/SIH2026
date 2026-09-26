"""
Short-Chain Jevons Elementary Index Engine for APIx Phase 3.
Implements the Jevons elementary link and recursive chaining per Methodology §19.
"""

from __future__ import annotations
import math
from decimal import Decimal
from typing import Dict, List, Optional
from .models import MatchedProduct, ElementaryIndexResult


class JevonsEngine:
    """
    Computes unweighted geometric elementary links and chains them over time:
        J_(s,t) = exp( 1/N * sum(ln P_(i,t) - ln P_(i,t-1)) )
        I_(s,t) = I_(s,t-1) * J_(s,t)
    """

    def __init__(self, base_value: Decimal = Decimal("100.00")):
        self.base_value = base_value
        # Historical chained index store: (stratum_id, period) -> Decimal
        self._chain_history: Dict[tuple[str, str], Decimal] = {}

    def get_chained_index(self, stratum_id: str, period: str) -> Optional[Decimal]:
        return self._chain_history.get((stratum_id, period))

    def set_base_index(self, stratum_id: str, base_period: str):
        self._chain_history[(stratum_id, base_period)] = self.base_value

    def compute_elementary_index(
        self,
        stratum_id: str,
        route: str,
        lead_time_class: str,
        period: str,
        prev_period: Optional[str],
        matched_products: List[MatchedProduct],
        eligible_count_prev: int,
        coverage_ratio: float,
        is_published: bool = True,
    ) -> ElementaryIndexResult:
        """
        Calculates Jevons link J_(s,t) and chains with previous period index I_(s,t-1).
        """
        n_matched = len(matched_products)

        if n_matched == 0 or not is_published:
            # Neutral link if no matched products or unpublished
            jevons_link = Decimal("1.000000")
        else:
            mean_log_diff = sum(m.log_price_relative for m in matched_products) / n_matched
            link_val = math.exp(mean_log_diff)
            jevons_link = Decimal(str(round(link_val, 6)))

        # Retrieve previous chained index, or initialize with base_value
        prev_index = None
        if prev_period:
            prev_index = self._chain_history.get((stratum_id, prev_period))

        if prev_index is None:
            prev_index = self.base_value

        chained_val = prev_index * jevons_link
        chained_index = Decimal(str(round(chained_val, 4)))

        # Update chain history for this period
        self._chain_history[(stratum_id, period)] = chained_index

        return ElementaryIndexResult(
            stratum_id=stratum_id,
            route=route,
            lead_time_class=lead_time_class,
            period=period,
            matched_count=n_matched,
            eligible_count_prev=eligible_count_prev,
            coverage_ratio=round(coverage_ratio, 4),
            jevons_link=jevons_link,
            chained_index=chained_index,
            is_published=is_published,
        )
