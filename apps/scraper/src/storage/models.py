"""
SQLAlchemy declarative models for the Airfare Index pipeline.

These models define the PostgreSQL schema and act as the single source
of truth for the persistence layer.

Design choices (per user approval):
- Explicit foreign keys and indexes.
- All monetary fields use NUMERIC (Decimal) type, never floating point.
- Enums are stored as strings (VARCHAR).
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from models.enums import (
    AvailabilityStatus,
    CabinClass,
    CollectionMode,
    CollectionStatus,
    JobLifecycleStatus,
    TripType,
)


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Core / Metadata Tables
# ---------------------------------------------------------------------------

class Source(Base):
    """
    Registry of all sources (airlines, OTAs).
    Spec §3, §49
    """
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # AIRLINE, OTA
    permitted_method: Mapped[str] = mapped_column(String(50), nullable=False)  # API, WEB
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class SchemaVersion(Base):
    """
    Tracks schema versions over time.
    """
    __tablename__ = "schema_versions"

    version: Mapped[str] = mapped_column(String(20), primary_key=True)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)


class AdapterVersion(Base):
    """
    Tracks adapter versions.
    """
    __tablename__ = "adapter_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id"), nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    deployed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("source_id", "version", name="uq_adapter_source_version"),
    )


# ---------------------------------------------------------------------------
# Collection Runs & Jobs
# ---------------------------------------------------------------------------

class CollectionRun(Base):
    """
    A logical batch of collection jobs (e.g., "Daily Collection").
    """
    __tablename__ = "collection_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. IN_PROGRESS, COMPLETED


class CollectionJob(Base):
    """
    What we intended to collect (e.g., DEL-BOM, T+7 on Indigo).
    """
    __tablename__ = "collection_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("collection_runs.id"), nullable=False, index=True)
    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, nullable=False)
    
    source_name: Mapped[str] = mapped_column(ForeignKey("sources.name"), nullable=False)
    
    origin: Mapped[str] = mapped_column(String(3), nullable=False)
    destination: Mapped[str] = mapped_column(String(3), nullable=False)
    travel_date: Mapped[date] = mapped_column(Date, nullable=False)
    lead_days: Mapped[int] = mapped_column(Integer, nullable=False)
    
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # JobLifecycleStatus string
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


# ---------------------------------------------------------------------------
# Observations
# ---------------------------------------------------------------------------

class RawObservationRecord(Base):
    """
    What the source returned (raw evidence).
    Corresponds to Pydantic RawObservation.
    """
    __tablename__ = "raw_observations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collection_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("collection_runs.id"), nullable=False, index=True)
    request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("collection_jobs.request_id"), nullable=False, index=True)
    
    source_name: Mapped[str] = mapped_column(ForeignKey("sources.name"), nullable=False)
    
    collection_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    collection_method: Mapped[str] = mapped_column(String(20), nullable=False)
    
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_evidence_uri: Mapped[str | None] = mapped_column(String, nullable=True)
    
    parser_version: Mapped[str] = mapped_column(String(20), nullable=False)
    adapter_version: Mapped[str] = mapped_column(String(20), nullable=False)

    __table_args__ = (
        Index("ix_raw_obs_source_time", "source_name", "collection_timestamp"),
    )


class FareObservationRecord(Base):
    """
    Canonical flight fare record.
    Corresponds to Pydantic FareObservation.
    """
    __tablename__ = "fare_observations"

    observation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collection_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("collection_runs.id"), nullable=False, index=True)
    
    source: Mapped[str] = mapped_column(ForeignKey("sources.name"), nullable=False)
    source_offer_id: Mapped[str | None] = mapped_column(String, nullable=True)
    source_itinerary_id: Mapped[str | None] = mapped_column(String, nullable=True)
    
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    travel_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    lead_days: Mapped[int] = mapped_column(Integer, nullable=False)
    
    origin: Mapped[str] = mapped_column(String(3), nullable=False)
    destination: Mapped[str] = mapped_column(String(3), nullable=False)
    
    airline: Mapped[str] = mapped_column(String(100), nullable=False)
    airline_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    flight_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    trip_type: Mapped[str] = mapped_column(String(20), nullable=False)
    cabin: Mapped[str] = mapped_column(String(20), nullable=False)
    passenger_count: Mapped[int] = mapped_column(Integer, nullable=False)
    
    departure_time_local: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    departure_time_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    arrival_time_local: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    arrival_time_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stops: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    fare_family: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fare_class: Mapped[str | None] = mapped_column(String(20), nullable=True)
    requires_self_transfer: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    
    # IMPORTANT: Money stored as NUMERIC, not Float
    base_fare: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    taxes: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    fees: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    discount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    total_fare: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    price_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    
    availability: Mapped[str] = mapped_column(String(20), nullable=False)
    
    raw_value_reference: Mapped[str | None] = mapped_column(String, nullable=True)
    raw_evidence_uri: Mapped[str | None] = mapped_column(String, nullable=True)
    
    adapter_version: Mapped[str] = mapped_column(String(20), nullable=False)
    normalizer_version: Mapped[str] = mapped_column(String(20), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(20), nullable=False)

    __table_args__ = (
        Index("ix_fare_obs_route", "origin", "destination"),
        Index("ix_fare_obs_airline", "airline"),
        Index("ix_fare_obs_lead_days", "lead_days"),
    )


# ---------------------------------------------------------------------------
# Exceptions and Mappings
# ---------------------------------------------------------------------------

class EntityMapping(Base):
    """
    Versioned deterministic mappings.
    Spec §16
    """
    __tablename__ = "entity_mappings"

    mapping_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # AIRLINE, AIRPORT
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    raw_value: Mapped[str] = mapped_column(String, nullable=False)
    canonical_value: Mapped[str] = mapped_column(String, nullable=False)
    
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    approval_status: Mapped[str] = mapped_column(String(50), nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __table_args__ = (
        Index("ix_entity_mappings_lookup", "entity_type", "source", "raw_value"),
    )


class NormalizationException(Base):
    """
    Exceptions caught during normalisation, sent to AI fallback.
    Spec §41
    """
    __tablename__ = "normalization_exceptions"

    exception_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    observation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=True)
    
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    field_name: Mapped[str] = mapped_column(String(50), nullable=False)
    raw_value: Mapped[str] = mapped_column(String, nullable=False)
    
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    ai_attempted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ai_candidate: Mapped[str | None] = mapped_column(String, nullable=True)
    ai_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    resolution_status: Mapped[str] = mapped_column(String(50), nullable=False)
    resolved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ValidationErrorRecord(Base):
    """
    Validation failures.
    """
    __tablename__ = "validation_errors"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collection_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("collection_runs.id"), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    
    error_type: Mapped[str] = mapped_column(String(50), nullable=False)  # PYDANTIC, BUSINESS
    field_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    raw_value: Mapped[str | None] = mapped_column(String, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


# ---------------------------------------------------------------------------
# Health & Metrics
# ---------------------------------------------------------------------------

class QualityMetric(Base):
    __tablename__ = "quality_metrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collection_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("collection_runs.id"), nullable=False, index=True)
    source: Mapped[str] = mapped_column(ForeignKey("sources.name"), nullable=False)
    
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    metric_dimensions: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class SourceHealth(Base):
    __tablename__ = "source_health"

    source: Mapped[str] = mapped_column(ForeignKey("sources.name"), primary_key=True)
    
    success_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    observation_yield: Mapped[float | None] = mapped_column(Float, nullable=True)
    parser_error_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    validation_error_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    normalization_error_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    response_time_p50: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_time_p95: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    rate_limit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    access_restriction_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_schema_change_detected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
