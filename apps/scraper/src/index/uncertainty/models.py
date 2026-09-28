"""
Data Models for Statistical Sampling Uncertainty & Confidence Intervals (§Roadmap Item 5).
"""

from __future__ import annotations
from decimal import Decimal
from typing import Dict, Optional
from pydantic import BaseModel, Field


class UncertaintyMetrics(BaseModel):
    """
    Statistical sampling uncertainty metrics for an index value.
    Distinguishes statistical sampling uncertainty from scraper/source error.
    """
    index_value: Decimal
    sample_size: int
    variance: Optional[float] = None
    standard_error: Optional[float] = None
    ci95_lower: Optional[float] = None
    ci95_upper: Optional[float] = None
    confidence_level: float = 0.95
    status: str = Field(
        ...,
        description="AVAILABLE or NOT_AVAILABLE (insufficient sample size, N < 2)"
    )
    aggregation_tier: str  # ELEMENTARY_STRATUM, LEAD_TIME, ROUTE, ALL_INDIA
    methodology: str = "DELTA_METHOD_LOG_JEVONS_PROPAGATION"
    provenance_note: str = (
        "Statistical uncertainty represents sampling variance of log price relatives across matched products. "
        "It is strictly separated from scraper or source observation counts."
    )
