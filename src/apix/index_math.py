"""
Index mathematics for APIx – Phase 4.

All functions are pure (no DB, no I/O) and return new values.
The aggregation ladder:

  band items → route-lead relative (Jevons / geometric mean)
             → route relative (weighted geometric mean over lead windows)
             → overall relative (weighted arithmetic mean over routes)
             → chained index level

This follows India's CPI 2024: Jevons at the elementary level,
Young-type aggregation above (weighted arithmetic mean at the top).
"""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import date
from statistics import median
from typing import Sequence


# ── Elementary level ──────────────────────────────────────────────────────

def jevons_mean(relatives: Sequence[float]) -> float | None:
    """
    Geometric mean of a sequence of price relatives (Jevons elementary aggregate).

    Returns None for an empty sequence.
    All relatives must be positive.
    """
    if not relatives:
        return None
    log_sum = sum(math.log(r) for r in relatives)
    return math.exp(log_sum / len(relatives))


# ── Weighted geometric mean ───────────────────────────────────────────────

def weighted_geomean(values: Sequence[float], weights: Sequence[float]) -> float | None:
    """
    Weighted geometric mean: exp(Σ w_i * ln(v_i)).

    Missing (zero-weight) items are skipped. Remaining weights are
    renormalised to sum to 1 before the computation.

    Returns None if no items remain after filtering.
    """
    pairs = [(v, w) for v, w in zip(values, weights) if w > 0 and v > 0]
    if not pairs:
        return None
    total_w = sum(w for _, w in pairs)
    log_sum = sum((w / total_w) * math.log(v) for v, w in pairs)
    return math.exp(log_sum)


# ── Weighted arithmetic mean ──────────────────────────────────────────────

def weighted_arith_mean(values: Sequence[float], weights: Sequence[float]) -> float | None:
    """
    Weighted arithmetic mean: Σ w_i * v_i (renormalising present weights).

    Returns None if no valid pairs exist.
    """
    pairs = [(v, w) for v, w in zip(values, weights) if w > 0]
    if not pairs:
        return None
    total_w = sum(w for _, w in pairs)
    return sum((w / total_w) * v for v, w in pairs)


# ── Item price statistic ──────────────────────────────────────────────────

def item_price(total_fares: Sequence[float], statistic: str = "min") -> float | None:
    """
    Return the price statistic for a group of eligible fares.

    statistic: 'min' | 'median'
    Returns None for an empty sequence.
    """
    if not total_fares:
        return None
    if statistic == "min":
        return min(total_fares)
    if statistic == "median":
        return median(total_fares)
    raise ValueError(f"Unknown price_statistic: {statistic!r}")


# ── Relative computation ──────────────────────────────────────────────────

def compute_item_relative(price_t: float, price_prev: float) -> float | None:
    """
    Compute P_t / P_prev.

    Returns None if either price is None or prev is zero.
    """
    if price_t is None or price_prev is None or price_prev == 0:
        return None
    return price_t / price_prev


# ── Coverage ─────────────────────────────────────────────────────────────

def compute_coverage(n_present: int, n_expected: int) -> float:
    """Coverage = present / expected. Returns 0 if expected is 0."""
    if n_expected == 0:
        return 0.0
    return n_present / n_expected


# ── Full aggregation ─────────────────────────────────────────────────────

def aggregate_index(
    item_relatives: dict[tuple[str, int, str], float],
    route_weights: dict[str, float],
    lead_weights: dict[int, float],
    prev_level: float,
    min_coverage: float,
    n_routes: int,
    n_leads: int,
    n_bands: int,
) -> tuple[float | None, float]:
    """
    Aggregate item relatives into an overall index level.

    Parameters
    ----------
    item_relatives
        Mapping (route, lead_days, dep_band) → relative for the current day.
    route_weights
        {route_id: weight}. May not sum to 1 if some routes are missing.
    lead_weights
        {lead_days_int: weight}
    prev_level
        The previous valid index level (used for chaining).
    min_coverage
        Below this fraction, return (None, coverage) – do not publish level.
    n_routes / n_leads / n_bands
        Total expected counts (for coverage denominator).

    Returns
    -------
    (level, coverage)
        level is None when coverage < min_coverage.
    """
    n_expected = n_routes * n_leads * n_bands
    n_present = len(item_relatives)
    coverage = compute_coverage(n_present, n_expected)

    if not item_relatives:
        return None, coverage

    # Step 1: for each (route, lead_days), compute Jevons over band relatives
    route_lead_jevons: dict[tuple[str, int], float] = {}
    for (route, lead, band), rel in item_relatives.items():
        cell = (route, lead)
        if cell not in route_lead_jevons:
            route_lead_jevons[cell] = []
        route_lead_jevons[cell].append(rel)  # type: ignore[assignment]

    route_lead_relatives: dict[tuple[str, int], float] = {}
    for (route, lead), rels in list(route_lead_jevons.items()):
        j = jevons_mean(rels)  # type: ignore[arg-type]
        if j is not None:
            route_lead_relatives[(route, lead)] = j

    # Step 2: for each route, compute weighted geometric mean over lead windows
    route_relatives: dict[str, float] = {}
    routes_present = {r for (r, _) in route_lead_relatives}
    for route in routes_present:
        leads = [ld for (r, ld) in route_lead_relatives if r == route]
        rels = [route_lead_relatives[(route, ld)] for ld in leads]
        wts = [lead_weights.get(ld, 0.0) for ld in leads]
        wgm = weighted_geomean(rels, wts)
        if wgm is not None:
            route_relatives[route] = wgm

    if not route_relatives:
        return None, coverage

    # Step 3: overall relative = weighted arithmetic mean of route relatives
    routes = list(route_relatives.keys())
    rels = [route_relatives[r] for r in routes]
    wts = [route_weights.get(r, 0.0) for r in routes]
    overall_rel = weighted_arith_mean(rels, wts)

    if overall_rel is None:
        return None, coverage

    # Step 4: check coverage threshold
    if coverage < min_coverage:
        return None, coverage

    # Step 5: chain
    level = prev_level * overall_rel
    return level, coverage


def aggregate_route_index(
    item_relatives: dict[tuple[str, int, str], float],
    route: str,
    lead_weights: dict[int, float],
    prev_level: float,
    min_coverage: float,
    n_leads: int,
    n_bands: int,
) -> tuple[float | None, float]:
    """
    Same chaining logic but for a single route's own index series.
    """
    route_items = {
        (r, ld, b): v for (r, ld, b), v in item_relatives.items() if r == route
    }
    n_expected = n_leads * n_bands
    n_present = len(route_items)
    coverage = compute_coverage(n_present, n_expected)

    if not route_items:
        return None, coverage

    # Jevons per lead window
    lead_jevons: dict[int, list[float]] = defaultdict(list)
    for (_, ld, _), rel in route_items.items():
        lead_jevons[ld].append(rel)

    lead_relatives: dict[int, float] = {}
    for ld, rels in lead_jevons.items():
        j = jevons_mean(rels)
        if j is not None:
            lead_relatives[ld] = j

    leads = list(lead_relatives.keys())
    rels = [lead_relatives[ld] for ld in leads]
    wts = [lead_weights.get(ld, 0.0) for ld in leads]
    wgm = weighted_geomean(rels, wts)

    if wgm is None or coverage < min_coverage:
        return None, coverage

    return prev_level * wgm, coverage
