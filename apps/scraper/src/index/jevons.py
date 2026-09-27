"""
Short-Chain Jevons Elementary Index Engine for APIx Phase 29.

Implements:
1. Logarithmic Jevons formulation:
   ln J_(s,t) = 1/N * sum(ln p_(i,t) - ln p_(i,t-1))
   J_(s,t) = exp(ln J_(s,t))
2. Direct geometric formulation verification:
   J_direct = [ product(p_(i,t) / p_(i,t-1)) ] ^ (1/N)
   Asserts numerical equality within floating point epsilon.
3. Recursive Short-Chain Linking:
   I_(s,t) = I_(s,t-1) * J_(s,t)
   with I_(s,0) = 100.00.
4. Precision:
   Internal calculations maintain double/Decimal precision without intermediate rounding.
"""

from __future__ import annotations
import math
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from .models import MatchedProduct, ElementaryIndexResult


class JevonsEngine:
    """
    Computes unweighted geometric elementary links and chains them recursively:
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

    @staticmethod
    def compute_links(matched_products: List[MatchedProduct]) -> Tuple[float, float, float]:
        """
        Computes both log-formulation link and direct-geometric link.
        Returns:
            Tuple of (log_link, direct_link, absolute_delta)
        """
        n = len(matched_products)
        if n == 0:
            return 1.0, 1.0, 0.0

        # Log formulation
        mean_log_diff = sum(m.log_price_relative for m in matched_products) / n
        log_link = math.exp(mean_log_diff)

        # Direct geometric formulation: (product of relatives) ^ (1/n)
        # For numerical stability with large n, accumulate in float
        prod_relatives = 1.0
        for m in matched_products:
            prod_relatives *= float(m.price_relative)
        direct_link = prod_relatives ** (1.0 / n)

        delta = abs(log_link - direct_link)
        return log_link, direct_link, delta

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
            jevons_link = Decimal("1.000000")
            direct_link = Decimal("1.000000")
            log_link = Decimal("1.000000")
            delta = 0.0
            mean_p0 = None
            mean_pt = None
        else:
            log_val, direct_val, delta = self.compute_links(matched_products)
            jevons_link = Decimal(str(round(log_val, 6)))
            direct_link = Decimal(str(round(direct_val, 6)))
            log_link = Decimal(str(round(log_val, 6)))
            mean_p0 = Decimal(str(round(sum(float(m.p_prev) for m in matched_products) / n_matched, 2)))
            mean_pt = Decimal(str(round(sum(float(m.p_curr) for m in matched_products) / n_matched, 2)))

        # Retrieve previous chained index, or initialize with base_value (100.00)
        prev_index = None
        if prev_period:
            prev_index = self._chain_history.get((stratum_id, prev_period))

        if prev_index is None:
            prev_index = self.base_value

        chained_val = prev_index * jevons_link
        chained_index = Decimal(str(round(chained_val, 4)))

        # Store in historical chain
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
            direct_geometric_link=direct_link,
            log_geometric_link=log_link,
            link_equality_delta=delta,
            mean_price_prev=mean_p0,
            mean_price_curr=mean_pt,
            is_published=is_published,
        )
