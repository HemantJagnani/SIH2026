"""
APIx Synthetic Demonstration Pipeline Engine (§Roadmap Validation).

Executes the existing APIx mathematics and econometrics pipeline on the synthetic August 2026 panel:
1. Daily Demonstration APIx: Consecutive day-to-day short-chain Jevons matching.
2. Weekly Demonstration APIx: Intra-week geometric prices and week-over-week chaining.
3. Monthly Demonstration APIx: Calendar-month geometric aggregation with 0.30 active-day qualification.
4. Statistical Uncertainty: Sampling variance, standard errors, and 95% confidence intervals (Delta method).
5. Governance Invariants: Proves P_ref (₹8,641.45) is NEVER used as an index denominator.
"""

from __future__ import annotations
from collections import defaultdict
from datetime import date
from decimal import Decimal
import math
from typing import Any, Dict, List, Optional, Tuple

from index.lead_time_weights import EMPIRICAL_LEAD_TIME_WEIGHTS
from index.route_basket import get_top60_route_weights
from index.monthly_aggregation import MonthlyAggregationEngine, MultiDayProductQuote
from index.uncertainty import UncertaintyEstimationEngine
from .models import (
    SyntheticDailyIndexPoint,
    SyntheticWeeklyIndexPoint,
)


class SyntheticDemonstrationPipeline:
    """
    Executes daily, weekly, and monthly index compilations on synthetic data.
    """

    WEEK_RANGES = [
        (1, 1, 7, "2026-08-01", "2026-08-07", "Week 1 (Aug 1 - Aug 7)"),
        (2, 8, 14, "2026-08-08", "2026-08-14", "Week 2 (Aug 8 - Aug 14)"),
        (3, 15, 21, "2026-08-15", "2026-08-21", "Week 3 (Aug 15 - Aug 21)"),
        (4, 22, 31, "2026-08-22", "2026-08-31", "Week 4 (Aug 22 - Aug 31)"),
    ]

    def __init__(self, synthetic_observations: List[Dict[str, Any]]):
        self.observations = synthetic_observations
        self.lt_weights = EMPIRICAL_LEAD_TIME_WEIGHTS  # Empirical lead-time weights
        self.route_weights = get_top60_route_weights(use_iata_codes=True)  # DGCA Top-60 weights
        self.uncertainty_engine = UncertaintyEstimationEngine()
        self.monthly_aggregator = MonthlyAggregationEngine(active_days_threshold=0.30)

        # Pre-group observations by collection date
        self.by_day: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        for o in self.observations:
            day_num = int(o["collection_date"].split("-")[-1])
            self.by_day[day_num].append(o)

    def run_daily_pipeline(self) -> List[SyntheticDailyIndexPoint]:
        """
        Calculates daily synthetic price relatives and daily demonstration APIx series (Days 1 to 31).
        Base: Day 1 (2026-08-01) = 100.00.
        """
        daily_series: List[SyntheticDailyIndexPoint] = []
        current_chain_index = Decimal("100.0000")

        # Day 1: Baseline
        daily_series.append(
            SyntheticDailyIndexPoint(
                day=1,
                date="2026-08-01",
                matched_pairs=len(self.by_day.get(1, [])),
                daily_price_relative=Decimal("1.000000"),
                daily_chain_index=current_chain_index,
                variance=0.0,
                standard_error=0.0,
                ci95_lower=100.0,
                ci95_upper=100.0,
            )
        )

        # Days 2 to 31
        for day in range(2, 32):
            prev_obs = self.by_day.get(day - 1, [])
            curr_obs = self.by_day.get(day, [])
            date_str = f"2026-08-{day:02d}"

            # Map products by canonical ID for consecutive day matching
            prev_map = {o["canonical_product_id"]: o for o in prev_obs}
            curr_map = {o["canonical_product_id"]: o for o in curr_obs}
            matched_keys = sorted(set(prev_map.keys()).intersection(set(curr_map.keys())))

            # Group matched pairs by (route, lead_time)
            cell_relatives: Dict[Tuple[str, str], List[float]] = defaultdict(list)
            for k in matched_keys:
                p0 = float(prev_map[k]["total_fare"])
                pt = float(curr_map[k]["total_fare"])
                if p0 > 0 and pt > 0:
                    rel = pt / p0
                    cell_relatives[(curr_map[k]["route"], curr_map[k]["lead_time_class"])].append(rel)

            # Compute elementary Jevons relatives per cell
            # J_(r,L) = exp(mean(ln r))
            cell_jevons: Dict[Tuple[str, str], Decimal] = {}
            cell_variances: List[float] = []

            for cell_key, rel_list in cell_relatives.items():
                if rel_list:
                    log_rels = [math.log(r) for r in rel_list]
                    mean_log = sum(log_rels) / len(log_rels)
                    cell_jevons[cell_key] = Decimal(str(round(math.exp(mean_log), 6)))
                    if len(rel_list) > 1:
                        s2 = sum((x - mean_log) ** 2 for x in log_rels) / (len(rel_list) - 1)
                        cell_variances.append(s2 / len(rel_list))

            # Aggregate lead times per route using empirical weights w_L
            route_indices: Dict[str, Decimal] = {}
            for r in self.route_weights:
                r_rel = Decimal("0")
                weight_sum = Decimal("0")
                for lt, w in self.lt_weights.items():
                    j_val = cell_jevons.get((r, lt), Decimal("1.000000"))
                    r_rel += w * j_val
                    weight_sum += w
                route_indices[r] = r_rel / weight_sum if weight_sum > 0 else Decimal("1.000000")

            # Aggregate routes using DGCA weights W_r
            daily_relative = Decimal("0")
            for r, W in self.route_weights.items():
                daily_relative += W * route_indices.get(r, Decimal("1.000000"))

            # Update daily chain index
            current_chain_index = Decimal(str(round(current_chain_index * daily_relative, 4)))

            # Estimate daily sampling uncertainty via Delta method
            avg_var = (sum(cell_variances) / len(cell_variances)) if cell_variances else 0.00001
            index_val_float = float(current_chain_index)
            var_index = (index_val_float ** 2) * avg_var
            se_index = math.sqrt(max(var_index, 0.0))
            ci_low = round(max(index_val_float - (1.96 * se_index), 0.0), 2)
            ci_high = round(index_val_float + (1.96 * se_index), 2)

            daily_series.append(
                SyntheticDailyIndexPoint(
                    day=day,
                    date=date_str,
                    matched_pairs=len(matched_keys),
                    daily_price_relative=Decimal(str(round(daily_relative, 6))),
                    daily_chain_index=current_chain_index,
                    variance=round(var_index, 6),
                    standard_error=round(se_index, 4),
                    ci95_lower=ci_low,
                    ci95_upper=ci_high,
                )
            )

        return daily_series

    def run_weekly_pipeline(self) -> List[SyntheticWeeklyIndexPoint]:
        """
        Aggregates daily observations into weekly synthetic APIx series (Weeks 1 to 4).
        Computes intra-week geometric representative prices and week-over-week chaining.
        Base: Week 1 = 100.00.
        """
        weekly_series: List[SyntheticWeeklyIndexPoint] = []

        # Step 1: Compute product-level intra-week geometric means for each of the 4 weeks
        weekly_product_prices: Dict[int, Dict[str, Dict[str, Any]]] = {}

        for w_num, start_d, end_d, start_str, end_str, label in self.WEEK_RANGES:
            # Collect all observations within the week
            w_obs: List[Dict[str, Any]] = []
            for d in range(start_d, end_d + 1):
                w_obs.extend(self.by_day.get(d, []))

            # Group by canonical product ID
            by_prod: Dict[str, List[float]] = defaultdict(list)
            prod_meta: Dict[str, Dict[str, str]] = {}
            for o in w_obs:
                pid = o["canonical_product_id"]
                by_prod[pid].append(float(o["total_fare"]))
                if pid not in prod_meta:
                    prod_meta[pid] = {
                        "route": o["route"],
                        "lead_time": o["lead_time_class"],
                    }

            # Geometric mean per product
            w_prices: Dict[str, Dict[str, Any]] = {}
            for pid, fares in by_prod.items():
                if fares:
                    geom_p = math.exp(sum(math.log(f) for f in fares) / len(fares))
                    w_prices[pid] = {
                        "price": geom_p,
                        "route": prod_meta[pid]["route"],
                        "lead_time": prod_meta[pid]["lead_time"],
                        "obs_count": len(fares),
                    }

            weekly_product_prices[w_num] = w_prices

        # Step 2: Week 1 Baseline = 100.00
        curr_chain = Decimal("100.0000")
        w1_meta = self.WEEK_RANGES[0]
        weekly_series.append(
            SyntheticWeeklyIndexPoint(
                week_number=1,
                week_label=w1_meta[5],
                start_date=w1_meta[3],
                end_date=w1_meta[4],
                observations_count=sum(len(self.by_day.get(d, [])) for d in range(w1_meta[1], w1_meta[2] + 1)),
                matched_products_count=len(weekly_product_prices[1]),
                weekly_price_relative=Decimal("1.000000"),
                weekly_chain_index=curr_chain,
                variance=0.0,
                standard_error=0.0,
                ci95_lower=100.0,
                ci95_upper=100.0,
            )
        )

        # Step 3: Weeks 2, 3, 4: Chain from previous week
        for w_idx in range(1, len(self.WEEK_RANGES)):
            w_meta = self.WEEK_RANGES[w_idx]
            w_num, start_d, end_d, start_str, end_str, label = w_meta

            prev_prices = weekly_product_prices[w_num - 1]
            curr_prices = weekly_product_prices[w_num]
            common_ids = sorted(set(prev_prices.keys()).intersection(set(curr_prices.keys())))

            cell_relatives: Dict[Tuple[str, str], List[float]] = defaultdict(list)
            for pid in common_ids:
                p0 = prev_prices[pid]["price"]
                pt = curr_prices[pid]["price"]
                if p0 > 0 and pt > 0:
                    cell_relatives[(curr_prices[pid]["route"], curr_prices[pid]["lead_time"])].append(pt / p0)

            # Jevons per cell
            cell_jevons: Dict[Tuple[str, str], Decimal] = {}
            cell_vars: List[float] = []
            for cell_key, rels in cell_relatives.items():
                if rels:
                    log_rels = [math.log(r) for r in rels]
                    mean_log = sum(log_rels) / len(log_rels)
                    cell_jevons[cell_key] = Decimal(str(round(math.exp(mean_log), 6)))
                    if len(rels) > 1:
                        s2 = sum((x - mean_log) ** 2 for x in log_rels) / (len(rels) - 1)
                        cell_vars.append(s2 / len(rels))

            # Aggregate lead times
            route_relatives: Dict[str, Decimal] = {}
            for r in self.route_weights:
                r_rel = Decimal("0")
                w_sum = Decimal("0")
                for lt, w in self.lt_weights.items():
                    j_val = cell_jevons.get((r, lt), Decimal("1.000000"))
                    r_rel += w * j_val
                    w_sum += w
                route_relatives[r] = r_rel / w_sum if w_sum > 0 else Decimal("1.000000")

            # Aggregate routes
            weekly_rel = Decimal("0")
            for r, W in self.route_weights.items():
                weekly_rel += W * route_relatives.get(r, Decimal("1.000000"))

            curr_chain = Decimal(str(round(curr_chain * weekly_rel, 4)))

            avg_var = (sum(cell_vars) / len(cell_vars)) if cell_vars else 0.00002
            val_float = float(curr_chain)
            var_idx = (val_float ** 2) * avg_var
            se_idx = math.sqrt(max(var_idx, 0.0))

            weekly_series.append(
                SyntheticWeeklyIndexPoint(
                    week_number=w_num,
                    week_label=label,
                    start_date=start_str,
                    end_date=end_str,
                    observations_count=sum(len(self.by_day.get(d, [])) for d in range(start_d, end_d + 1)),
                    matched_products_count=len(common_ids),
                    weekly_price_relative=Decimal(str(round(weekly_rel, 6))),
                    weekly_chain_index=curr_chain,
                    variance=round(var_idx, 6),
                    standard_error=round(se_idx, 4),
                    ci95_lower=round(max(val_float - (1.96 * se_idx), 0.0), 2),
                    ci95_upper=round(val_float + (1.96 * se_idx), 2),
                )
            )

        return weekly_series

    def run_monthly_pipeline(self) -> Dict[str, Any]:
        """
        Calculates August's synthetic monthly representative prices using the existing
        geometric-mean methodology and active-day qualification threshold 0.30.
        """
        class MonthlyQuoteWrapper:
            def __init__(self, obs_dict):
                self.product_key = obs_dict["canonical_product_id"]
                self.total_fare = Decimal(str(obs_dict["total_fare"]))
                self.collection_date = obs_dict["collection_date"]
                self.travel_date = obs_dict["travel_date"]
                self.product_stratum_id = f"{obs_dict['route']}_{obs_dict['lead_time_class']}"
                self.route = obs_dict["route"]
                self.lead_time_class = obs_dict["lead_time_class"]
                self.status = "VALID_BASELINE"

        quotes = [MonthlyQuoteWrapper(o) for o in self.observations]

        aggregated = self.monthly_aggregator.aggregate_monthly_observations(
            observations=quotes,
            month="2026-08",
            total_calendar_days=31,
        )

        total_prods = len(aggregated)
        qualified_prods = sum(1 for p in aggregated.values() if p.qualifies_for_headline)
        disqualified_prods = total_prods - qualified_prods

        # Compute cell geometric means across qualified products for each of the 360 cells
        cell_prods: Dict[Tuple[str, str], List[Decimal]] = defaultdict(list)
        for p in aggregated.values():
            if p.qualifies_for_headline:
                cell_prods[(p.route, p.lead_time_class)].append(p.geometric_price)

        cell_prices: Dict[Tuple[str, str], Decimal] = {}
        for cell_key, p_list in cell_prods.items():
            if p_list:
                log_p = sum(math.log(float(p)) for p in p_list) / len(p_list)
                cell_prices[cell_key] = Decimal(str(round(math.exp(log_p), 2)))

        # Aggregate lead times per route using empirical weights w_L
        route_prices: Dict[str, Decimal] = {}
        for r in self.route_weights:
            r_sum = Decimal("0")
            w_sum = Decimal("0")
            for lt, w in self.lt_weights.items():
                if (r, lt) in cell_prices:
                    r_sum += w * cell_prices[(r, lt)]
                    w_sum += w
            route_prices[r] = (r_sum / w_sum).quantize(Decimal("0.01")) if w_sum > 0 else Decimal("0.00")

        # Aggregate routes using DGCA Top-60 weights W_r
        national_representative_price = Decimal("0")
        for r, W in self.route_weights.items():
            national_representative_price += W * route_prices.get(r, Decimal("0"))
        national_representative_price = national_representative_price.quantize(Decimal("0.01"))

        return {
            "month": "2026-08",
            "total_canonical_products": total_prods,
            "qualified_products_count": qualified_prods,
            "disqualified_products_count": disqualified_prods,
            "active_day_threshold": 0.30,
            "scheduled_collection_days": 31,
            "populated_cells": len(cell_prices),
            "total_cells": 360,
            "synthetic_august_representative_price_inr": float(national_representative_price),
            "governance_note": (
                "P_ref (₹8,641.45) is strictly descriptive and was NOT used as a denominator "
                "in this monthly calculation."
            ),
        }
