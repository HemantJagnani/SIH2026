"""
APIx Index Engine — Core Statistical Calculations.

This module is COMPLETELY INDEPENDENT of FastAPI, database, or any web framework.
All functions are pure, deterministic, and independently unit-testable.

DISCLAIMER: All formulas and weights herein are ILLUSTRATIVE POC METHODOLOGY.
They are NOT official CPI methodology. Subject to validation against MoSPI,
DGCA and international price-index standards.
"""
from __future__ import annotations

import statistics
from typing import Optional


def calculate_median_fare(fares: list[float]) -> Optional[float]:
    """
    Calculate the median of a list of valid fares.

    Args:
        fares: List of valid (non-null, non-outlier) fare values.

    Returns:
        Median fare, or None if the list is empty.
    """
    if not fares:
        return None
    return statistics.median(fares)


def detect_outlier(fare: float, group_median: float, threshold: float = 3.0) -> tuple[bool, Optional[str]]:
    """
    Flag an observation as a potential outlier using a transparent robust rule.

    Rule (POC quality-control, NOT an official statistical standard):
        price > threshold × group_median → outlier

    Args:
        fare: The total fare to check.
        group_median: Median of the same date/route/lead_days group.
        threshold: Multiplier (default 3.0).

    Returns:
        Tuple of (is_outlier, reason_string).
    """
    if group_median <= 0:
        return False, None
    if fare > threshold * group_median:
        reason = (
            f"Fare {fare:.2f} exceeds {threshold}× group median {group_median:.2f} "
            f"(POC quality-control rule, not an official statistical standard)"
        )
        return True, reason
    return False, None


def calculate_route_price(
    lead_time_fares: dict[int, Optional[float]],
    lead_time_weights: dict[int, float],
) -> Optional[float]:
    """
    Combine lead-time median fares into a single representative route price.

    Formula (illustrative POC):
        route_price = Σ (lead_time_weight × lead_time_median_price)

    Only lead times with valid (non-None) prices contribute.
    If ALL lead times are missing, return None.

    Args:
        lead_time_fares:   {lead_days: median_fare | None}
        lead_time_weights: {lead_days: weight}

    Returns:
        Weighted representative route price, or None if no valid data.
    """
    total_weight = 0.0
    weighted_sum = 0.0

    for lead_days, median_fare in lead_time_fares.items():
        weight = lead_time_weights.get(lead_days, 0.0)
        if median_fare is not None and weight > 0:
            weighted_sum += weight * median_fare
            total_weight += weight

    if total_weight == 0:
        return None

    # Re-normalise if some lead times are missing
    return weighted_sum / total_weight


def calculate_route_index(
    current_price: Optional[float],
    base_price: float,
) -> Optional[float]:
    """
    Calculate the price relative (index) for a single route.

    Formula:
        RouteIndex(r, t) = (CurrentPrice(r, t) / BasePrice(r)) × 100

    Args:
        current_price: Current representative route price.
        base_price:    Illustrative POC base-period price.

    Returns:
        Route index value, or None if current_price is missing.
    """
    if current_price is None or base_price <= 0:
        return None
    return (current_price / base_price) * 100.0


def calculate_airfare_index(
    route_indices: dict[str, Optional[float]],
    route_weights: dict[str, float],
) -> Optional[float]:
    """
    Calculate the overall Airfare Price Index (APIx).

    Formula (illustrative POC, weighted arithmetic):
        APIx(t) = Σ [route_weight(r) × RouteIndex(r, t)]

    Only routes with valid (non-None) indices contribute.
    Weights are re-normalised if some routes are missing.

    Args:
        route_indices: {route_code: index_value | None}
        route_weights: {route_code: weight}

    Returns:
        APIx value (rounded to 4 decimal places), or None if no valid routes.
    """
    total_weight = 0.0
    weighted_sum = 0.0

    for route_code, index_value in route_indices.items():
        weight = route_weights.get(route_code, 0.0)
        if index_value is not None and weight > 0:
            weighted_sum += weight * index_value
            total_weight += weight

    if total_weight == 0:
        return None

    raw = weighted_sum / total_weight
    return round(raw, 4)


def calculate_daily_change(
    current_index: Optional[float],
    previous_index: Optional[float],
) -> Optional[float]:
    """
    Calculate the daily percentage change in the index.

    Formula:
        DailyChangePct = (APIx(t) - APIx(t-1)) / APIx(t-1) × 100

    Args:
        current_index:  Today's APIx value.
        previous_index: Yesterday's APIx value.

    Returns:
        Percentage change (rounded to 4 decimal places), or None.
    """
    if current_index is None or previous_index is None or previous_index == 0:
        return None
    return round((current_index - previous_index) / previous_index * 100.0, 4)


def calculate_monthly_index(daily_indices: list[float]) -> Optional[float]:
    """
    Calculate the monthly APIx as the mean of valid daily APIx values.

    NOTE: This is a POC aggregation rule, not an official statistical standard.

    Args:
        daily_indices: List of valid daily index values in the month.

    Returns:
        Monthly average APIx, or None if no valid data.
    """
    valid = [v for v in daily_indices if v is not None]
    if not valid:
        return None
    return round(sum(valid) / len(valid), 4)


def calculate_period_change(
    current_value: Optional[float],
    reference_value: Optional[float],
) -> Optional[float]:
    """
    Calculate percentage change between any two index periods.

    Used for MoM and YoY calculations.

    Args:
        current_value:   Current period index.
        reference_value: Reference period index.

    Returns:
        Percentage change (rounded to 4 decimal places), or None.
    """
    if current_value is None or reference_value is None or reference_value == 0:
        return None
    return round((current_value - reference_value) / reference_value * 100.0, 4)
