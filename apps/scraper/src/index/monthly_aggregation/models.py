"""
Data Models for Multi-Day Calendar-Month Collection & Aggregation (§Roadmap Item 4).
"""

from __future__ import annotations
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional, Set
from pydantic import BaseModel, Field


class MultiDayProductQuote(BaseModel):
    """A single flight quote observed on a specific collection date."""
    collection_date: date
    travel_date: date
    lead_time_class: str
    total_fare: Decimal
    product_key: str
    stratum_id: str
    source: str = "google_flights"


class MonthlyAggregatedProduct(BaseModel):
    """
    Within-month geometric price for an individual product across multiple collection dates.
    Tracks active-day qualification per Methodology.
    """
    product_key: str
    stratum_id: str
    route: str
    lead_time_class: str
    month: str  # YYYY-MM
    geometric_price: Decimal
    observation_count: int
    active_days_observed: int
    total_calendar_days: int
    active_days_ratio: float
    qualifies_for_headline: bool
    qualification_threshold: float = 0.30
    qualification_status: str  # QUALIFIED_HEADLINE or BELOW_ACTIVE_DAYS_THRESHOLD
    collection_dates: List[str] = Field(default_factory=list)
    travel_dates: List[str] = Field(default_factory=list)
    provenance: str = "MULTI_DAY_GEOMETRIC_AGGREGATION"
