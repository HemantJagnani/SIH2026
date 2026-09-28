"""
Continuous Multi-Day Monthly Aggregation Engine (§Roadmap Item 4).

Aggregates multiple daily observations across a calendar month into representative
geometric product prices, preserving collection_date and travel_date separately,
and enforcing active-day qualification logic with configurable 0.30 threshold.
"""

from __future__ import annotations
import math
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence

from .models import MonthlyAggregatedProduct


class MonthlyAggregationEngine:
    """
    Computes within-month geometric product prices:
        P̄_(i,t) = exp( 1/K * sum(ln P_(i,t,k)) )
    across multi-day collections within a calendar month.
    """

    DEFAULT_THRESHOLD = 0.30

    def __init__(self, active_days_threshold: float = DEFAULT_THRESHOLD):
        self.active_days_threshold = active_days_threshold

    @staticmethod
    def get_days_in_month(month_str: str) -> int:
        """Determines calendar days in YYYY-MM."""
        y, m = map(int, month_str.split("-"))
        if m in (1, 3, 5, 7, 8, 10, 12):
            return 31
        elif m in (4, 6, 9, 11):
            return 30
        else:
            # Leap year check
            is_leap = (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)
            return 29 if is_leap else 28

    def aggregate_monthly_observations(
        self,
        observations: Sequence[Any],
        month: str,
        total_calendar_days: Optional[int] = None,
    ) -> Dict[str, MonthlyAggregatedProduct]:
        """
        Groups observations by homogeneous product key for the month.
        Preserves collection_date and travel_date independently.
        """
        cal_days = total_calendar_days or self.get_days_in_month(month)
        grouped: Dict[str, List[Any]] = defaultdict(list)

        for obs in observations:
            fare = getattr(obs, "total_fare", Decimal("0"))
            if fare <= Decimal("0"):
                continue

            status = getattr(obs, "quality_status", None) or getattr(obs, "status", None)
            if status not in ("VALID", "VALID_BASELINE"):
                continue

            prod_key = (
                getattr(obs, "product_key", None)
                or getattr(obs, "offer_fingerprint", None)
                or f"{getattr(obs, 'airline', '')}_{getattr(obs, 'flight_number', '')}_{getattr(obs, 'route', '')}"
            )
            grouped[prod_key].append(obs)

        results: Dict[str, MonthlyAggregatedProduct] = {}

        for prod_key, obs_list in sorted(grouped.items()):
            # Extract collection dates and travel dates separately
            coll_dates: List[str] = []
            travel_dates: List[str] = []

            log_sum = 0.0
            for o in obs_list:
                f_val = float(getattr(o, "total_fare"))
                log_sum += math.log(f_val)

                c_date = (
                    getattr(o, "collection_date", None)
                    or (str(getattr(o, "search_timestamp", ""))[:10] if getattr(o, "search_timestamp", None) else None)
                    or (str(getattr(o, "collected_at", ""))[:10] if getattr(o, "collected_at", None) else None)
                )
                if c_date:
                    coll_dates.append(str(c_date))

                t_date = getattr(o, "travel_date", None)
                if t_date:
                    travel_dates.append(str(t_date))

            distinct_coll_dates = sorted(set(coll_dates))
            distinct_travel_dates = sorted(set(travel_dates))
            active_days_count = len(distinct_coll_dates)
            ratio = active_days_count / float(cal_days)

            geom_fare = math.exp(log_sum / len(obs_list))
            first = obs_list[0]

            is_qualified = ratio >= self.active_days_threshold
            qual_status = "QUALIFIED_HEADLINE" if is_qualified else "BELOW_ACTIVE_DAYS_THRESHOLD"

            results[prod_key] = MonthlyAggregatedProduct(
                product_key=prod_key,
                stratum_id=getattr(first, "product_stratum_id", "") or "STRATUM_DEFAULT",
                route=getattr(first, "route", "DEL-BOM"),
                lead_time_class=getattr(first, "lead_time_class", "T+7"),
                month=month,
                geometric_price=Decimal(str(round(geom_fare, 2))),
                observation_count=len(obs_list),
                active_days_observed=active_days_count,
                total_calendar_days=cal_days,
                active_days_ratio=round(ratio, 4),
                qualifies_for_headline=is_qualified,
                qualification_threshold=self.active_days_threshold,
                qualification_status=qual_status,
                collection_dates=distinct_coll_dates,
                travel_dates=distinct_travel_dates,
            )

        return results
