"""
Data Models for APIx Phase 3 Statistical Index Compilation.
Defines MonthlyProductPrice, MatchedProduct, ElementaryIndexResult,
LeadTimeIndexResult, RouteIndexResult, and APIxSeriesResult per Methodology §12, §19, §21, §22, §68.
"""

from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class MonthlyProductPrice(BaseModel):
    """Monthly geometric mean price for a single homogeneous product i in month t."""
    product_id: str = Field(..., description="Unique product key or offer_fingerprint")
    stratum_id: str = Field(..., description="ProductStratum ID")
    route: str = Field(..., description="e.g. DEL-BOM")
    lead_time_class: str = Field(..., description="e.g. T+1, T+7, T+15, T+21, T+30, T+45")
    month: str = Field(..., description="Period format YYYY-MM")
    geometric_price: Decimal = Field(..., gt=Decimal("0"), description="Geometric mean price")
    observation_count: int = Field(..., ge=1, description="Number of valid observations in month")
    active_days: int = Field(..., ge=1, description="Number of distinct days product was observed")
    source_count: int = Field(default=1, ge=1, description="Number of distinct sources observed")
    quality_status: str = Field(default="VALID", description="VALID, REPLACED, etc.")


class MatchedProduct(BaseModel):
    """A matched product pair across period t-1 and period t."""
    product_id: str
    stratum_id: str
    p_prev: Decimal = Field(..., gt=Decimal("0"))
    p_curr: Decimal = Field(..., gt=Decimal("0"))
    price_relative: Decimal = Field(..., gt=Decimal("0"))
    log_price_relative: float


class ElementaryIndexResult(BaseModel):
    """Short-chain Jevons elementary index result for homogeneous stratum s in month t."""
    stratum_id: str
    route: str
    lead_time_class: str
    period: str
    matched_count: int = Field(..., ge=0)
    eligible_count_prev: int = Field(..., ge=0)
    coverage_ratio: float = Field(..., ge=0.0, le=1.0)
    jevons_link: Decimal = Field(..., description="J_(s,t) unweighted geometric mean link")
    chained_index: Decimal = Field(..., description="I_(s,t) chained elementary index")
    is_published: bool = Field(default=True, description="True if passes minimum coverage thresholds")


class LeadTimeIndexResult(BaseModel):
    """Lead-time aggregated index for route r and lead-time class l in month t."""
    route: str
    lead_time_class: str
    period: str
    index_value: Decimal
    strata_count: int


class RouteIndexResult(BaseModel):
    """Route-level index I_(r,t) aggregated across lead-time classes."""
    route: str
    period: str
    index_value: Decimal
    lead_times_included: List[str]


class APIxSeriesResult(BaseModel):
    """All-India APIx final price index series output per Methodology §68."""
    index_name: str = "India Airfare Price Index"
    frequency: str = "monthly"
    period: str
    reference_period: str = "2024"
    base_value: Decimal = Decimal("100.00")
    index_value: Decimal
    mom_percent: Optional[Decimal] = None
    yoy_percent: Optional[Decimal] = None
    route_indices: Dict[str, Decimal] = Field(default_factory=dict)
    lead_time_indices: Dict[str, Decimal] = Field(default_factory=dict)
    methodology_version: str = "APIx v1.0"
    weight_version: str = "2026.09"
    published_at: datetime = Field(default_factory=datetime.utcnow)
