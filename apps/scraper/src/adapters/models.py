"""
Data models for the Core Adapter Interfaces.

Spec sections:
- §6: Common collection request (FareSearchRequest)
- §11: Raw evidence (metadata tracking)
- §12: Collection status
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from models.observation import CabinClass, FareObservation, TripType


class CollectionMode(str, Enum):
    """How the adapter interacts with the source."""
    API = "API"
    HTTP = "HTTP"
    BROWSER = "BROWSER"


class FareSearchRequest(BaseModel):
    """
    Common collection request that ALL adapters must accept.
    Spec §6.
    """
    model_config = ConfigDict(frozen=True)

    request_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    source: str = Field(..., description="The name of the source (e.g. 'indigo')")
    
    origin: str = Field(..., min_length=3, max_length=3, description="IATA code")
    destination: str = Field(..., min_length=3, max_length=3, description="IATA code")
    travel_date: date
    lead_days: int
    
    trip_type: TripType = Field(default=TripType.ONE_WAY)
    cabin: CabinClass = Field(default=CabinClass.ECONOMY)
    
    adults: int = Field(default=1, ge=1)
    children: int = Field(default=0, ge=0)
    infants: int = Field(default=0, ge=0)
    
    currency: str = Field(default="INR", min_length=3, max_length=3)
    collection_mode: CollectionMode

    @model_validator(mode="after")
    def validate_route(self) -> "FareSearchRequest":
        """Origin and destination must be different."""
        if self.origin.upper() == self.destination.upper():
            raise ValueError(f"Origin and destination cannot be the same ({self.origin})")
        return self


class CollectionStatus(str, Enum):
    """Explicit result of a collection attempt per Spec §12."""
    SUCCESS = "SUCCESS"
    NO_RESULTS = "NO_RESULTS"
    SOLD_OUT = "SOLD_OUT"
    NOT_FOUND = "NOT_FOUND"
    SOURCE_ERROR = "SOURCE_ERROR"
    TIMEOUT = "TIMEOUT"
    RATE_LIMITED = "RATE_LIMITED"
    ACCESS_RESTRICTED = "ACCESS_RESTRICTED"
    CAPTCHA_PRESENT = "CAPTCHA_PRESENT"
    PARSER_ERROR = "PARSER_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NORMALIZATION_ERROR = "NORMALIZATION_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class CollectionResult(BaseModel):
    """
    Final output of an adapter's `collect()` method.
    Contains both the parsed data and the required operational evidence.
    Spec §11 and §12.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Core data
    status: CollectionStatus
    observations: list[FareObservation] = Field(default_factory=list)
    
    # Evidence / diagnostics
    collection_run_id: uuid.UUID | None = None
    request_id: uuid.UUID
    collection_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    source_url_or_endpoint_reference: str | None = None
    http_status: int | None = None
    response_time_ms: int | None = None
    raw_evidence_uri: str | None = None
    content_type: str | None = None
    
    adapter_version: str
    parser_version: str
    
    error_message: str | None = None
