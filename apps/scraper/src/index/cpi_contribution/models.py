"""
Data Models for Urban/Rural CPI Contribution (§Roadmap Item 9).
"""

from __future__ import annotations
from decimal import Decimal
from typing import Dict, Optional
from pydantic import BaseModel, Field


class SectoralCPIContribution(BaseModel):
    """
    Sector-disaggregated airfare contribution to headline consumer inflation in percentage points (pp).
    Derived from MoSPI CPI 2024 Annexure 5.3d Item 07.3.3.1.2.01.
    Calculated strictly from APIx percentage inflation change, never from APIx level.
    """
    period: str
    apix_inflation_rate_percent: Decimal = Field(..., description="APIx percentage change (MoM or YoY)")
    cpi_combined_contribution_pp: Decimal = Field(..., description="Combined All-India airfare contribution in pp")
    cpi_urban_contribution_pp: Decimal = Field(..., description="Urban sector airfare contribution in pp")
    cpi_rural_contribution_pp: Decimal = Field(..., description="Rural sector airfare contribution in pp")
    cpi_airfare_weight_combined_percent: Decimal = Field(default=Decimal("0.02951"))
    cpi_airfare_weight_urban_percent: Decimal = Field(default=Decimal("0.017843"))
    cpi_airfare_weight_rural_percent: Decimal = Field(default=Decimal("0.011666"))
    provenance_reference: str = "MoSPI CPI 2024 Annexure 5.3d Item 07.3.3.1.2.01"
    disclaimer: str = (
        "Airfare contribution in percentage points is calculated as APIx percentage change * weight / 100. "
        "It is strictly an inflation contribution and must never be computed from the absolute APIx level."
    )
