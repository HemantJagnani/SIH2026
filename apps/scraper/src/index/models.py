"""
Data Models for APIx Phase 29 Statistical Index Compilation.

Defines:
- MonthlyProductPrice
- MatchedProduct
- ElementaryIndexResult (with log/direct geometric proof)
- LeadTimeIndexResult
- RouteIndexResult (with explicit prototype median retained)
- APIxSeriesResult (supporting monthly CPI-compatible and high-frequency indicator outputs)
"""

from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MonthlyProductPrice(BaseModel):
    """Monthly geometric mean price for a single homogeneous product i in month t."""
    product_id: str = Field(..., description="Unique product key or offer_fingerprint")
    stratum_id: str = Field(..., description="ProductStratum ID")
    route: str = Field(..., description="e.g. DEL-BOM")
    lead_time_class: str = Field(..., description="e.g. T+1, T+7, T+15, T+21, T+30, T+45")
    month: str = Field(..., description="Period format YYYY-MM")
    geometric_price: Decimal = Field(..., gt=Decimal("0"), description="Geometric mean price in INR")
    observation_count: int = Field(..., ge=1, description="Number of valid observations in month")
    active_days: int = Field(..., ge=1, description="Number of distinct days product was observed")
    source: str = Field(default="google_flights", description="Primary data source")
    source_count: int = Field(default=1, ge=1, description="Number of distinct sources observed")
    quality_status: str = Field(default="VALID", description="VALID, REPLACED, QUALITY_ADJUSTED, etc.")


class MatchedProduct(BaseModel):
    """A matched product pair across period t-1 and period t."""
    product_id: str
    stratum_id: str
    p_prev: Decimal = Field(..., gt=Decimal("0"))
    p_curr: Decimal = Field(..., gt=Decimal("0"))
    price_relative: Decimal = Field(..., gt=Decimal("0"))
    log_price_relative: float
    is_quality_adjusted: bool = False
    net_quality_adjustment_inr: Decimal = Decimal("0.00")
    replacement_id: Optional[str] = None


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
    chained_index: Decimal = Field(..., description="I_(s,t) chained elementary index (Base=100.00)")
    direct_geometric_link: Optional[Decimal] = Field(default=None, description="Direct product of relatives ^ (1/N)")
    log_geometric_link: Optional[Decimal] = Field(default=None, description="exp(mean(log relatives))")
    link_equality_delta: Optional[float] = Field(default=None, description="abs(direct - log) for verification")
    mean_price_prev: Optional[Decimal] = None
    mean_price_curr: Optional[Decimal] = None
    is_published: bool = Field(default=True, description="True if passes minimum coverage thresholds")


class LeadTimeIndexResult(BaseModel):
    """Lead-time aggregated index for route r and lead-time class l in month t."""
    route: str
    lead_time_class: str
    period: str
    index_value: Decimal
    strata_count: int
    coverage_ratio: float = 1.0
    weight: Decimal = Decimal("0.166667")
    weight_label: str = "PROVISIONAL EQUAL LEAD-TIME WEIGHTS"


class RouteIndexResult(BaseModel):
    """Route-level index I_(r,t) aggregated across lead-time classes."""
    route: str
    period: str
    index_value: Decimal
    lead_times_included: List[str]
    lead_time_weights: Dict[str, Decimal]
    elementary_indices_by_lead_time: Dict[str, Decimal]
    
    # Retained diagnostic prototype indicator per Phase 29 §2 & §19
    prototype_median_indicator: Optional[Decimal] = Field(
        default=None,
        description="DEL_BOM_PROTOTYPE_MEDIAN_INDICATOR (retained diagnostic indicator)"
    )
    prototype_representative_price_inr: Optional[Decimal] = Field(
        default=None,
        description="Weighted representative price using lead-time medians"
    )

    # Formal Reference Period Taxonomy Fields
    index_reference_period: str = Field(default="2024=100", description="MoSPI official index reference (2024=100)")
    price_reference_period: str = Field(default="calendar-year 2024 average (Pending Historical Actuals)", description="Official MoSPI price reference period")
    weight_reference_period: str = Field(default="HCES 2023-24", description="Household Consumption Expenditure Survey 2023-24")
    chain_link_period: str = Field(default="December y-1 (Eurostat) / Month-over-Month (MoSPI)", description="Annual linking point")

    # Project Experimental Reference (PROVISIONAL_PROJECT_REFERENCE)
    reference_type: str = Field(default="PROVISIONAL_PROJECT_REFERENCE", description="Reference classification type")
    experimental_project_reference_price: Decimal = Field(default=Decimal("6632.67"), description="First complete production run weighted representative price")
    experimental_reference_period: str = Field(default="2026-09-26", description="First complete production run collection date")

    reference_price: Decimal = Field(default=Decimal("6632.67"), description="Active reference price")
    reference_price_method: str = Field(default="Option B — first production run weighted representative price", description="Calculation methodology")
    reference_price_source: str = Field(default="production_run_825fa969", description="Source run ID or dataset")
    reference_index_value: Decimal = Field(default=Decimal("100.00"), description="Index value at reference period")
    methodology_version: str = Field(default="APIx v2.0 (MoSPI CPI 2024 + Eurostat HICP Aligned)", description="Engine methodology version")


class APIxSeriesResult(BaseModel):
    """All-India APIx final price index series output per Methodology §12, §13, §14."""
    index_name: str = "India Airfare Price Index"
    series_type: str = "MONTHLY_CPI_COMPATIBLE"  # or HIGH_FREQUENCY_INDICATOR
    period: str

    # Explicit Reference Taxonomy Fields (Replacing ambiguous base terminology)
    index_reference_period: str = Field(default="2024=100", description="MoSPI official index reference (2024=100)")
    price_reference_period: str = Field(default="calendar-year 2024 average (Pending Historical Actuals)", description="Official MoSPI price reference period")
    weight_reference_period: str = Field(default="HCES 2023-24", description="Household Consumption Expenditure Survey 2023-24")
    chain_link_period: str = Field(default="December y-1 (Eurostat) / Month-over-Month (MoSPI)", description="Annual linking point")

    # Project Experimental Reference (Clearly distinguished from official MoSPI price reference)
    reference_type: str = Field(default="PROVISIONAL_PROJECT_REFERENCE", description="Reference classification type")
    experimental_project_reference_price: Decimal = Field(default=Decimal("6632.67"), description="First complete production run weighted representative price")
    experimental_reference_period: str = Field(default="2026-09-26", description="First complete production run collection date")

    reference_price: Decimal = Field(default=Decimal("6632.67"), description="Active reference price")
    reference_price_method: str = Field(default="Option B — first production run weighted representative price", description="Calculation methodology")
    reference_price_source: str = Field(default="production_run_825fa969", description="Source run ID or dataset")
    reference_index_value: Decimal = Field(default=Decimal("100.00"), description="Index value at reference period")

    # Backward compatibility aliases (Explicit aliases only)
    reference_period: str = "2026-09"
    base_value: Decimal = Field(default=Decimal("100.00"), description="Explicit alias for reference_index_value")
    base_price: Optional[Decimal] = Field(default=Decimal("6632.67"), description="Explicit alias for experimental_project_reference_price")
    base_period: Optional[str] = Field(default="2026-09-26", description="Explicit alias for experimental_reference_period")

    index_value: Decimal
    mom_percent: Optional[Decimal] = None
    yoy_percent: Optional[Decimal] = None
    route_indices: Dict[str, Decimal] = Field(default_factory=dict)
    lead_time_indices: Dict[str, Decimal] = Field(default_factory=dict)
    elementary_results: List[ElementaryIndexResult] = Field(default_factory=list)
    diagnostics_meta: Dict[str, Any] = Field(default_factory=dict)
    
    # Source diagnostics per Phase 29 §7
    source_diagnostics: Dict[str, Any] = Field(default_factory=dict)
    
    # Retained prototype median calculation per Phase 29 §2 & §19
    prototype_median_indicator: Optional[Dict[str, Any]] = None
    
    # MoSPI COICOP & CPI Integration
    coicop_classification: Dict[str, str] = Field(default_factory=dict)
    cpi_integration: Dict[str, Any] = Field(default_factory=dict)
    
    # Versioning & Audit Trail
    collection_run_id: str = "PHASE28-29-RUN-DELBOM"
    methodology_version: str = "APIx v2.0 (MoSPI CPI 2024 + Eurostat HICP Aligned)"
    product_definition_version: str = "APIx_PRODUCT_DEF_v2.0_FROZEN"
    weight_version: str = "2026.09-v2"
    quality_adjustment_version: str = "EUROSTAT_HICP_2024_QA_v1.0"
    published_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
