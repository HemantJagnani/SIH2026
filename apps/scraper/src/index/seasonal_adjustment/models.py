"""
Data Models for Seasonal Adjustment & Moving-Holiday Analysis (§Roadmap Item 8).
"""

from __future__ import annotations
from decimal import Decimal
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class SeasonalAdjustmentResult(BaseModel):
    """
    Output of analytical seasonal adjustment.
    Headline APIx is kept completely unadjusted; output is labeled SEASONALLY_ADJUSTED_ANALYTICAL.
    """
    period: str
    headline_unadjusted_apix: Decimal
    seasonally_adjusted_apix: Optional[Decimal] = None
    seasonal_factor: Optional[Decimal] = None
    trend_cycle_component: Optional[Decimal] = None
    irregular_component: Optional[Decimal] = None
    status: str = Field(
        ...,
        description="SEASONALLY_ADJUSTED_ANALYTICAL or NOT_AVAILABLE (insufficient time series, < 36 months)"
    )
    methodology: str = "X13_ARIMA_SEATS_MOVING_HOLIDAY"
    reason: Optional[str] = None
    governance_disclaimer: str = (
        "Headline APIx is strictly unadjusted. Seasonally adjusted series is an analytical output only "
        "and never displaces the official unadjusted consumer price index."
    )
