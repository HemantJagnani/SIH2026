"""
Data Models for Synthetic August 2026 Longitudinal Demonstration (§Roadmap Validation).

CRITICAL GOVERNANCE INVARIANT:
This dataset is SYNTHETIC and MUST NEVER be presented or cited as observed historical
Indian airfare data. It exists solely to validate daily, weekly, and monthly APIx
econometric pipelines without waiting for future real collection rounds.
"""

from __future__ import annotations
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


SYNTHETIC_GENERATION_VERSION = "AUG2026_DEMO_V1"
SYNTHETIC_DATA_STATUS = "SYNTHETIC"


class SyntheticFareObservation(BaseModel):
    """
    A single synthetic airfare quote for August 2026.
    Explicitly marked as SYNTHETIC across all metadata fields.
    """
    observation_id: str
    data_status: str = Field(default=SYNTHETIC_DATA_STATUS, description="Always SYNTHETIC")
    synthetic: bool = Field(default=True, description="Always True for synthetic records")
    synthetic_generation_version: str = Field(default=SYNTHETIC_GENERATION_VERSION)

    # Collection & Travel Timestamps (strictly segregated)
    collection_date: str = Field(..., description="YYYY-MM-DD collection date in August 2026")
    collection_month: str = Field(default="2026-08")
    travel_date: str = Field(..., description="YYYY-MM-DD forward-looking travel date")
    lead_time_class: str = Field(..., description="T+1, T+7, T+15, T+21, T+30, T+45")
    lead_days: int

    # Product Characteristics
    route: str
    origin: str
    destination: str
    airline: str
    flight_number: str
    departure_time_local: str
    departure_time_band: str
    stops: int = 0
    stop_category: str = "NON_STOP"
    cabin: str = "ECONOMY"
    fare_family: str = "STANDARD"
    passenger_type: str = "ADULT"
    baggage_allowance_kg: int = 15

    # Econometric Price
    total_fare: Decimal = Field(..., gt=Decimal("0"))
    currency: str = "INR"

    # Fingerprinting & Tracking
    canonical_product_id: str
    product_fingerprint: str
    source: str = "google_flights"
    status: str = "VALID_BASELINE"


class SyntheticDailyIndexPoint(BaseModel):
    """Result of a daily synthetic APIx calculation."""
    day: int
    date: str
    matched_pairs: int
    daily_price_relative: Decimal
    daily_chain_index: Decimal
    variance: Optional[float] = None
    standard_error: Optional[float] = None
    ci95_lower: Optional[float] = None
    ci95_upper: Optional[float] = None


class SyntheticWeeklyIndexPoint(BaseModel):
    """Result of a weekly synthetic APIx calculation."""
    week_number: int
    week_label: str
    start_date: str
    end_date: str
    observations_count: int
    matched_products_count: int
    weekly_price_relative: Decimal
    weekly_chain_index: Decimal
    variance: Optional[float] = None
    standard_error: Optional[float] = None
    ci95_lower: Optional[float] = None
    ci95_upper: Optional[float] = None


class SyntheticAugustMetadata(BaseModel):
    """Metadata describing the synthetic August 2026 demonstration dataset."""
    dataset_name: str = "APIx_Synthetic_August_2026_Longitudinal_Demonstration"
    source_real_dataset: str = "11,716-observation production baseline (runtime/top60_observation_classification.json)"
    data_status: str = SYNTHETIC_DATA_STATUS
    synthetic: bool = True
    synthetic_generation_version: str = SYNTHETIC_GENERATION_VERSION
    random_seed: int = 42
    generation_date_utc: str
    number_of_collection_days: int = 31
    number_of_synthetic_observations: int
    route_count: int = 60
    lead_time_count: int = 6
    cell_count: int = 360
    canonical_product_pool_size: int
    average_daily_observations: float
    price_generation_methodology: str
    assumptions: List[str]
    disclaimer: str
