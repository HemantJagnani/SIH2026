"""
Data Models for Dynamic Hedonic Quality Adjustment (§Roadmap Item 3).
"""

from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class HedonicModelStatus(str, Enum):
    DATA_DEPENDENT_INACTIVE = "DATA_DEPENDENT_INACTIVE"
    CALIBRATED_ACTIVE = "CALIBRATED_ACTIVE"
    INSUFFICIENT_SAMPLE_SIZE = "INSUFFICIENT_SAMPLE_SIZE"
    COLLINEARITY_DETECTED = "COLLINEARITY_DETECTED"


class HedonicCoefficient(BaseModel):
    variable_name: str
    coefficient: float
    standard_error: Optional[float] = None
    p_value: Optional[float] = None
    provenance: str = "ESTIMATED_RIDGE_OLS"


class HedonicModelDiagnostics(BaseModel):
    sample_size: int
    r_squared: float
    adj_r_squared: float
    rmse: float
    condition_number: float
    f_statistic: Optional[float] = None
    training_period: str
    trained_at_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class HedonicAdjustmentResult(BaseModel):
    is_fallback: bool
    status: HedonicModelStatus
    predicted_delta_ln_price: float
    net_quality_adjustment_inr: Decimal
    adjusted_price_inr: Decimal
    valuation_method: str = "HEDONIC_LOG_LINEAR"
    model_version: str
    diagnostics: Optional[HedonicModelDiagnostics] = None
    rationale: str
