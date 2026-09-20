"""
Data cleaning and validation pipeline.

Validates raw observations, assigns quality_status, flags outliers,
and marks duplicates. Raw data is NEVER destroyed per spec §42.
"""
from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import date
from typing import Optional

from app.services.index_engine.calculator import calculate_median_fare, detect_outlier
from app.services.ingestion.source_adapter import RawFareObservation


VALID_FARE_CLASSES = {"economy", "business", "premium_economy", "first"}
VALID_AVAILABILITIES = {"available", "sold_out", "limited"}


def validate_observation(obs: RawFareObservation) -> tuple[str, Optional[str]]:
    """
    Validate a raw observation.

    Returns:
        (quality_status, rejection_reason)
        quality_status: 'valid' | 'invalid' | 'missing'
    """
    # Missing price
    if obs.total_fare is None and obs.availability == "available":
        return "missing", "Total fare is null but availability is 'available'"

    # Sold-out with price is allowed (some sources report it)
    if obs.availability == "sold_out":
        return "missing", "Observation is sold_out — no price available"

    if obs.total_fare is not None:
        if obs.total_fare < 0:
            return "invalid", f"Negative total_fare: {obs.total_fare}"
        if obs.total_fare == 0:
            return "invalid", "Zero total_fare is not valid"

    if obs.currency != "INR":
        return "invalid", f"Unexpected currency: {obs.currency} (only INR supported)"

    if not obs.origin or not obs.destination:
        return "invalid", "Missing origin or destination"

    if obs.origin == obs.destination:
        return "invalid", "Origin and destination are the same"

    if obs.lead_days <= 0:
        return "invalid", f"Invalid lead_days: {obs.lead_days}"

    if obs.fare_class not in VALID_FARE_CLASSES:
        return "invalid", f"Unsupported fare_class: {obs.fare_class}"

    if obs.passenger_count < 1:
        return "invalid", f"Invalid passenger_count: {obs.passenger_count}"

    return "valid", None


def make_duplicate_key(obs: RawFareObservation) -> str:
    """
    Create a canonical deduplication key.

    Key components (per spec §3):
        source + airline + origin + destination + travel_date + lead_days + fare_class
    """
    raw = "|".join([
        obs.source_name,
        obs.airline_code,
        obs.origin,
        obs.destination,
        str(obs.travel_date),
        str(obs.lead_days),
        obs.fare_class,
    ])
    return hashlib.md5(raw.encode()).hexdigest()


class CleaningResult:
    """Result of cleaning a single observation."""

    def __init__(
        self,
        obs: RawFareObservation,
        quality_status: str,
        rejection_reason: Optional[str],
        outlier_flag: bool,
        outlier_reason: Optional[str],
        duplicate_group_id: Optional[str],
        is_duplicate: bool,
    ) -> None:
        self.obs = obs
        self.quality_status = quality_status
        self.rejection_reason = rejection_reason
        self.outlier_flag = outlier_flag
        self.outlier_reason = outlier_reason
        self.duplicate_group_id = duplicate_group_id
        self.is_duplicate = is_duplicate


def clean_observations(
    raw_observations: list[RawFareObservation],
) -> list[CleaningResult]:
    """
    Run the full cleaning pipeline over a batch of raw observations.

    Pipeline:
        1. Validation → quality_status
        2. Duplicate detection → duplicate_group_id, mark duplicates as 'duplicate'
        3. Outlier detection → outlier_flag, outlier_reason

    Raw data is preserved; only flags are set.
    """
    results: list[CleaningResult] = []

    # ── Step 1: Validation ───────────────────────────────────────────────────
    for obs in raw_observations:
        quality_status, rejection_reason = validate_observation(obs)
        results.append(CleaningResult(
            obs=obs,
            quality_status=quality_status,
            rejection_reason=rejection_reason,
            outlier_flag=False,
            outlier_reason=None,
            duplicate_group_id=None,
            is_duplicate=False,
        ))

    # ── Step 2: Duplicate detection ──────────────────────────────────────────
    seen_keys: dict[str, int] = {}  # key → first result index
    for i, result in enumerate(results):
        key = make_duplicate_key(result.obs)
        result.duplicate_group_id = key
        if key in seen_keys:
            # This is a duplicate — mark it but do NOT delete the raw record
            result.is_duplicate = True
            if result.quality_status == "valid":
                result.quality_status = "duplicate"
        else:
            seen_keys[key] = i

    # ── Step 3: Outlier detection (only on valid observations) ───────────────
    # Group valid observations by (travel_date, route, lead_days)
    group_fares: dict[tuple, list[float]] = defaultdict(list)
    for result in results:
        if result.quality_status == "valid" and result.obs.total_fare is not None:
            group_key = (
                result.obs.travel_date,
                result.obs.origin,
                result.obs.destination,
                result.obs.lead_days,
            )
            group_fares[group_key].append(result.obs.total_fare)

    # Calculate group medians
    group_medians: dict[tuple, Optional[float]] = {
        k: calculate_median_fare(v) for k, v in group_fares.items()
    }

    # Apply outlier flag
    for result in results:
        if result.quality_status == "valid" and result.obs.total_fare is not None:
            group_key = (
                result.obs.travel_date,
                result.obs.origin,
                result.obs.destination,
                result.obs.lead_days,
            )
            median = group_medians.get(group_key)
            if median is not None:
                is_out, reason = detect_outlier(result.obs.total_fare, median)
                result.outlier_flag = is_out
                result.outlier_reason = reason

    return results
