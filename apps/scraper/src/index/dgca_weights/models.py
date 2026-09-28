"""
Data Models for DGCA Annual Route-Weight Updates & Basket Transitions (§Roadmap Item 10).
"""

from __future__ import annotations
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class RouteTransitionStatus(str, Enum):
    RETAINED = "RETAINED"
    NEW_ENTRANT = "NEW_ENTRANT"
    EXIT = "EXIT"


class RouteWeightTransitionRecord(BaseModel):
    """Tracks a route entering, exiting, or changing share between annual baskets."""
    route: str
    previous_rank: Optional[int] = None
    new_rank: Optional[int] = None
    previous_weight: Optional[Decimal] = None
    new_weight: Optional[Decimal] = None
    delta_weight: Optional[Decimal] = None
    transition_status: RouteTransitionStatus


class AnnualRouteBasket(BaseModel):
    """Versioned annual DGCA domestic passenger traffic basket."""
    basket_id: str
    reference_year: str  # e.g., 'CY2024', 'CY2025'
    status: str = Field(..., description="ACTIVE_PRODUCTION or PENDING_OFFICIAL_DGCA_PUBLICATION")
    route_count: int = 60
    total_basket_passengers: int
    total_national_passengers: int
    coverage_percent: Decimal
    weights: Dict[str, Decimal] = Field(default_factory=dict)
    transitions: List[RouteWeightTransitionRecord] = Field(default_factory=list)
    published_date: Optional[str] = None
    provenance_reference: str
