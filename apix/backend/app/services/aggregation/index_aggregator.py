"""
Index Aggregation Service.

Orchestrates the full pipeline:
  valid observations → route daily prices → route indices → APIx.
"""
from __future__ import annotations

import structlog
from collections import defaultdict
from datetime import date
from typing import Optional

from app.core.config import settings
from app.services.index_engine.calculator import (
    calculate_airfare_index,
    calculate_daily_change,
    calculate_median_fare,
    calculate_route_index,
    calculate_route_price,
)

logger = structlog.get_logger(__name__)


def compute_route_daily_prices(
    observations: list[dict],  # list of dicts with keys: travel_date, origin, destination, lead_days, total_fare, quality_status, outlier_flag
    lead_time_weights: dict[int, float] | None = None,
) -> dict[tuple[date, str, str], dict]:
    """
    For each (travel_date, route, lead_days), compute the median valid fare.

    Excludes invalid, duplicate, and outlier observations from the median.
    Missing prices return None (not zero).

    Returns:
        dict keyed by (travel_date, origin, destination) →
            { lead_days: {representative_price, observation_count, valid_count, missing_count, outlier_count} }
    """
    if lead_time_weights is None:
        lead_time_weights = settings.LEAD_TIME_WEIGHTS

    # Group valid (non-outlier, non-duplicate) fares
    group_fares: dict[tuple, list[float]] = defaultdict(list)
    group_counts: dict[tuple, dict] = defaultdict(lambda: {
        "total": 0, "valid": 0, "missing": 0, "outlier": 0
    })

    for obs in observations:
        key = (
            obs["travel_date"],
            obs["origin"],
            obs["destination"],
            obs["lead_days"],
        )
        counts = group_counts[key]
        counts["total"] += 1

        qs = obs.get("quality_status", "valid")
        outlier = obs.get("outlier_flag", False)
        fare = obs.get("total_fare")

        if qs in ("invalid", "duplicate"):
            continue
        if qs == "missing" or fare is None:
            counts["missing"] += 1
            continue
        if outlier:
            counts["outlier"] += 1
            continue

        counts["valid"] += 1
        group_fares[key].append(float(fare))

    # Calculate medians
    results: dict[tuple, dict] = {}
    for key, fares in group_fares.items():
        travel_date, origin, destination, lead_days = key
        route_key = (travel_date, origin, destination)
        if route_key not in results:
            results[route_key] = {}
        counts = group_counts[key]
        results[route_key][lead_days] = {
            "representative_price": calculate_median_fare(fares),
            "observation_count": counts["total"],
            "valid_observation_count": counts["valid"],
            "missing_count": counts["missing"],
            "outlier_count": counts["outlier"],
        }

    # Also fill in keys that only had missing/outlier observations
    for key, counts in group_counts.items():
        travel_date, origin, destination, lead_days = key
        route_key = (travel_date, origin, destination)
        if route_key not in results:
            results[route_key] = {}
        if lead_days not in results[route_key]:
            results[route_key][lead_days] = {
                "representative_price": None,
                "observation_count": counts["total"],
                "valid_observation_count": counts["valid"],
                "missing_count": counts["missing"],
                "outlier_count": counts["outlier"],
            }

    return results


def compute_route_index_for_date(
    search_date: date,
    route_code: str,
    origin: str,
    destination: str,
    route_observations: list[dict],
    lead_time_weights: dict[int, float] | None = None,
    base_prices: dict[str, float] | None = None,
    route_weights: dict[str, float] | None = None,
) -> dict:
    """
    Calculate the route price and index for a specific route on a specific date.
    """
    if lead_time_weights is None:
        lead_time_weights = settings.LEAD_TIME_WEIGHTS
    if base_prices is None:
        base_prices = settings.BASE_PRICES
    if route_weights is None:
        route_weights = settings.ROUTE_WEIGHTS

    # Get lead-time median fares
    lead_time_fares: dict[int, Optional[float]] = {}
    for lt in lead_time_weights:
        matching = [
            obs for obs in route_observations
            if (
                obs.get("lead_days") == lt
                and obs.get("quality_status") == "valid"
                and not obs.get("outlier_flag", False)
                and obs.get("total_fare") is not None
            )
        ]
        fares = [obs["total_fare"] for obs in matching]
        lead_time_fares[lt] = calculate_median_fare(fares)

    current_price = calculate_route_price(lead_time_fares, lead_time_weights)
    base_price = base_prices.get(route_code, 6000.0)
    route_index = calculate_route_index(current_price, base_price)
    route_weight = route_weights.get(route_code, 0.0)
    contribution = round(route_weight * route_index, 6) if route_index is not None else None

    return {
        "date": search_date,
        "route_code": route_code,
        "origin": origin,
        "destination": destination,
        "base_price": base_price,
        "current_price": current_price,
        "route_index": route_index,
        "route_weight": route_weight,
        "contribution": contribution,
        "lead_time_fares": lead_time_fares,
    }
