"""Pydantic v2 schemas for API request/response models."""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    timestamp: datetime


# ---------------------------------------------------------------------------
# Index
# ---------------------------------------------------------------------------

class CurrentIndexResponse(BaseModel):
    date: date
    index_value: float
    daily_change_pct: Optional[float]
    weekly_change_pct: Optional[float]
    monthly_change_pct: Optional[float]
    observation_count: int
    coverage_pct: Optional[float]
    disclaimer: str = (
        "Illustrative POC methodology — subject to validation against "
        "MoSPI, DGCA and international price-index standards."
    )


class IndexHistoryPoint(BaseModel):
    date: date
    index_value: Optional[float]
    daily_change_pct: Optional[float]


class IndexHistoryResponse(BaseModel):
    data: list[IndexHistoryPoint]
    count: int
    start_date: date
    end_date: date


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

class LeadTimePrice(BaseModel):
    lead_days: int
    representative_price: Optional[float]
    observation_count: int
    valid_observation_count: int


class RouteResponse(BaseModel):
    route_code: str
    origin: str
    destination: str
    weight: float
    base_price: float
    current_price: Optional[float]
    route_index: Optional[float]
    contribution: Optional[float]
    lead_time_prices: list[LeadTimePrice] = []
    date: Optional[date]
    disclaimer: str = "Illustrative POC route weight — not an official weight."


class RoutesListResponse(BaseModel):
    data: list[RouteResponse]
    count: int
    disclaimer: str = "Illustrative POC methodology."


class RouteHistoryPoint(BaseModel):
    date: date
    route_index: Optional[float]
    current_price: Optional[float]


class RouteDetailResponse(BaseModel):
    route_code: str
    origin: str
    destination: str
    weight: float
    base_price: float
    current_price: Optional[float]
    route_index: Optional[float]
    contribution: Optional[float]
    lead_time_prices: list[LeadTimePrice] = []
    history: list[RouteHistoryPoint] = []
    date: Optional[date]
    disclaimer: str = "Illustrative POC methodology."


# ---------------------------------------------------------------------------
# Observations
# ---------------------------------------------------------------------------

class ObservationSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_id: int
    airline_id: int
    route_id: int
    search_timestamp: datetime
    travel_date: date
    lead_days: int
    fare_class: str
    passenger_count: int
    base_fare: Optional[float]
    taxes: Optional[float]
    airport_charges: Optional[float]
    convenience_fee: Optional[float]
    total_fare: Optional[float]
    currency: str
    availability: str
    quality_status: str
    outlier_flag: bool
    outlier_reason: Optional[str]
    created_at: datetime

    # Joined fields
    airline_code: Optional[str] = None
    airline_name: Optional[str] = None
    route_code: Optional[str] = None
    source_name: Optional[str] = None


class ObservationsResponse(BaseModel):
    data: list[ObservationSchema]
    count: int
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Data Quality
# ---------------------------------------------------------------------------

class DataQualityResponse(BaseModel):
    total_observations: int
    valid: int
    invalid: int
    missing: int
    sold_out: int
    duplicates: int
    outliers: int
    coverage_pct: float
    disclaimer: str = "Data quality metrics based on synthetic POC data."


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------

class IngestionRunRequest(BaseModel):
    days: Optional[int] = Field(default=None, description="Number of synthetic days to generate")
    seed: Optional[int] = Field(default=None, description="Random seed for reproducibility")


class IngestionRunResponse(BaseModel):
    task_id: str
    message: str
    status: str
