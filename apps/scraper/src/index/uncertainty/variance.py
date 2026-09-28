"""
Statistical Sampling Uncertainty & Variance Propagation Engine (§Roadmap Item 5).

Implements:
1. Variance of log price relatives at the elementary Jevons level:
       Var(ln J_(s,t)) = 1 / (N * (N - 1)) * sum( (ln r_i - mean(ln r))^2 )
2. Delta-method propagation to elementary chained index and higher tiers:
       Var(I_(s,t)) ≈ I_(s,t)^2 * Var(ln J_(s,t))
3. Linear uncertainty propagation across lead-time weights and route weights.
4. Non-fabrication guard: Returns NOT_AVAILABLE / None if sample size N < 2.
"""

from __future__ import annotations
import math
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence

from .models import UncertaintyMetrics


class UncertaintyEstimationEngine:
    """
    Computes and propagates sampling variance and confidence intervals for APIx series.
    """

    CRITICAL_VALUE_95 = 1.95996  # Standard normal two-tailed 95% critical value

    def compute_elementary_uncertainty(
        self,
        matched_products: Sequence[Any],
        chained_index_value: Decimal,
        stratum_id: str = "STRATUM",
    ) -> UncertaintyMetrics:
        """
        Calculates variance of log price relatives at the elementary level.
        Never manufactures confidence intervals if N < 2.
        """
        n = len(matched_products)
        val_float = float(chained_index_value)

        if n < 2:
            return UncertaintyMetrics(
                index_value=chained_index_value,
                sample_size=n,
                variance=None,
                standard_error=None,
                ci95_lower=None,
                ci95_upper=None,
                status="NOT_AVAILABLE",
                aggregation_tier="ELEMENTARY_STRATUM",
                provenance_note=f"Insufficient sample size (N={n} < 2) in stratum {stratum_id}. Statistical variance cannot be estimated.",
            )

        log_relatives = [float(getattr(m, "log_price_relative")) for m in matched_products]
        mean_log = sum(log_relatives) / n

        # Sample variance of log relatives: s^2 = 1/(n-1) * sum((x - mean)^2)
        sample_var = sum((x - mean_log) ** 2 for x in log_relatives) / (n - 1)

        # Variance of the mean log relative (variance of ln J): s^2 / n
        var_ln_j = sample_var / n

        # Delta method for chained index: Var(I) ≈ I^2 * Var(ln J)
        var_index = (val_float ** 2) * var_ln_j
        se_index = math.sqrt(var_index)

        ci_lower = max(val_float - (self.CRITICAL_VALUE_95 * se_index), 0.0)
        ci_upper = val_float + (self.CRITICAL_VALUE_95 * se_index)

        return UncertaintyMetrics(
            index_value=chained_index_value,
            sample_size=n,
            variance=round(var_index, 6),
            standard_error=round(se_index, 4),
            ci95_lower=round(ci_lower, 4),
            ci95_upper=round(ci_upper, 4),
            status="AVAILABLE",
            aggregation_tier="ELEMENTARY_STRATUM",
            provenance_note=f"Elementary sampling uncertainty derived from {n} matched product pairs.",
        )

    def propagate_higher_level_uncertainty(
        self,
        elementary_uncertainties: Dict[str, UncertaintyMetrics],
        stratum_to_route_lead: Dict[str, tuple[str, str]],
        lead_time_weights: Dict[str, Decimal],
        route_weights: Dict[str, Decimal],
        headline_apix_val: Decimal,
    ) -> UncertaintyMetrics:
        """
        Propagates uncertainty to the All-India headline index using the Delta method
        over two-tier weighted linear aggregation.
        """
        val_float = float(headline_apix_val)
        available_variances = [
            u for u in elementary_uncertainties.values() if u.status == "AVAILABLE" and u.variance is not None
        ]

        if not available_variances:
            return UncertaintyMetrics(
                index_value=headline_apix_val,
                sample_size=0,
                variance=None,
                standard_error=None,
                ci95_lower=None,
                ci95_upper=None,
                status="NOT_AVAILABLE",
                aggregation_tier="ALL_INDIA",
                provenance_note="Zero elementary strata with sufficient sample size (N >= 2). Headline uncertainty NOT_AVAILABLE.",
            )

        # Group elementary variances by (route, lead_time)
        from collections import defaultdict
        strata_by_rl: Dict[tuple[str, str], list[float]] = defaultdict(list)

        for s_id, u in elementary_uncertainties.items():
            if u.status == "AVAILABLE" and u.variance is not None:
                r, l = stratum_to_route_lead.get(s_id, ("DEL-BOM", "T+7"))
                strata_by_rl[(r, l)].append(u.variance)

        # 1. Lead-time variance: Var(I_rl) = 1/K^2 * sum(Var(I_s))
        var_by_rl: Dict[tuple[str, str], float] = {}
        for (r, l), var_list in strata_by_rl.items():
            k = len(var_list)
            var_by_rl[(r, l)] = sum(var_list) / (k ** 2) if k > 0 else 0.0

        # 2. Route variance: Var(I_r) = sum_l (w_l^2 * Var(I_rl))
        var_by_route: Dict[str, float] = defaultdict(float)
        for (r, l), v_rl in var_by_rl.items():
            w_l = float(lead_time_weights.get(l, Decimal("0.166667")))
            var_by_route[r] += (w_l ** 2) * v_rl

        # 3. All-India variance: Var(APIx) = sum_r (W_r^2 * Var(I_r))
        var_apix = 0.0
        total_sample = sum(u.sample_size for u in available_variances)

        for r, v_r in var_by_route.items():
            W_r = float(route_weights.get(r, Decimal("0.0")))
            var_apix += (W_r ** 2) * v_r

        se_apix = math.sqrt(var_apix)
        ci_lower = max(val_float - (self.CRITICAL_VALUE_95 * se_apix), 0.0)
        ci_upper = val_float + (self.CRITICAL_VALUE_95 * se_apix)

        return UncertaintyMetrics(
            index_value=headline_apix_val,
            sample_size=total_sample,
            variance=round(var_apix, 6),
            standard_error=round(se_apix, 4),
            ci95_lower=round(ci_lower, 4),
            ci95_upper=round(ci_upper, 4),
            status="AVAILABLE",
            aggregation_tier="ALL_INDIA",
            provenance_note=f"Headline sampling uncertainty propagated across {len(available_variances)} qualifying elementary strata.",
        )
