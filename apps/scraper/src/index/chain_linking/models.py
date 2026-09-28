"""
Data Models for Annual December Chain-Linking (§Roadmap Item 7).
"""

from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class AnnualLinkRecord(BaseModel):
    """Annual link factor record linking December y-1 to the historical index reference."""
    link_year: int
    link_month: str = "12"  # December
    chain_link_factor: Decimal
    reference_base_year: str = "2024=100"
    december_index_value: Decimal
    weights_version: str
    recorded_at_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AnnualChainSeries(BaseModel):
    """Long-term multi-year chained APIx series."""
    series_id: str = "APIx_MULTI_YEAR_CHAINED"
    base_year: str = "2024=100"
    status: str = Field(
        ...,
        description="ACTIVE or DATA_DEPENDENT_INACTIVE (requires multiple annual baskets)"
    )
    published_links: Dict[int, AnnualLinkRecord] = Field(default_factory=dict)
    monthly_indices: Dict[str, Decimal] = Field(default_factory=dict)
    disclaimer: str = (
        "Annual chain-linking links successive annual baskets at December. "
        "Previously published index values are never retrospectively overwritten."
    )
