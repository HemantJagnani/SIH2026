"""
Data Models for Longitudinal Multi-Period Collection & Matching (§Roadmap Item 1).
"""

from __future__ import annotations
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from index.models import MatchedProduct, MonthlyProductPrice


class LongitudinalTargetCell(BaseModel):
    """A target cell for collection in period t1."""
    route: str
    lead_time_class: str
    lead_days: int
    target_travel_date: date
    collection_period: str = Field(..., description="e.g. '2026-10' or '2026-11'")
    status: str = "PENDING_COLLECTION"


class LongitudinalMatchingResult(BaseModel):
    """Result of cross-period matching between period t0 and period t1."""
    period_t0: str
    period_t1: str
    collection_timestamp_t0: Optional[str] = None
    collection_timestamp_t1: Optional[str] = None
    total_strata_evaluated: int
    matched_strata_count: int
    unmatched_strata_count: int
    total_matched_product_pairs: int
    matched_products_by_stratum: Dict[str, List[MatchedProduct]] = Field(default_factory=dict)
    eligible_products_t0_count: int
    eligible_products_t1_count: int
    longitudinal_coverage_ratio: float
    status: str = Field(
        ...,
        description="LONGITUDINAL_MATCH_READY, INSUFFICIENT_LONGITUDINAL_DATA, or NO_COMPARABLE_PRODUCTS"
    )
    can_calculate_monthly_index: bool
    governance_disclaimer: str = (
        "Price relatives are computed strictly between matched longitudinal products across distinct collection periods. "
        "No monthly index may be calculated unless valid comparable product pairs exist."
    )
