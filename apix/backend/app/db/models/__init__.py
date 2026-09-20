"""SQLAlchemy ORM models for the APIx database."""
import datetime
from datetime import datetime as dt
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Route(Base):
    """Represents a flight route (e.g., DEL-BOM)."""
    __tablename__ = "routes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    origin: Mapped[str] = mapped_column(String(3), nullable=False, index=True)
    destination: Mapped[str] = mapped_column(String(3), nullable=False, index=True)
    route_code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    weight: Mapped[float] = mapped_column(Float, nullable=False, comment="Illustrative POC route weight")
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[dt] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[dt] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    observations: Mapped[list["FareObservation"]] = relationship("FareObservation", back_populates="route")
    daily_prices: Mapped[list["RouteDailyPrice"]] = relationship("RouteDailyPrice", back_populates="route")
    indices: Mapped[list["RouteIndex"]] = relationship("RouteIndex", back_populates="route")


class Airline(Base):
    """Represents an airline carrier."""
    __tablename__ = "airlines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[dt] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    observations: Mapped[list["FareObservation"]] = relationship("FareObservation", back_populates="airline")


class Source(Base):
    """Represents a data source (airline direct / OTA mock)."""
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="airline_direct | ota_mock")
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[dt] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    observations: Mapped[list["FareObservation"]] = relationship("FareObservation", back_populates="source")


class FareObservation(Base):
    """
    Raw fare observation. Raw data is NEVER destroyed.
    Quality flags are added; the original record is always preserved.
    """
    __tablename__ = "fare_observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(Integer, ForeignKey("sources.id"), nullable=False, index=True)
    airline_id: Mapped[int] = mapped_column(Integer, ForeignKey("airlines.id"), nullable=False, index=True)
    route_id: Mapped[int] = mapped_column(Integer, ForeignKey("routes.id"), nullable=False, index=True)
    search_timestamp: Mapped[dt] = mapped_column(DateTime(timezone=True), nullable=False)
    travel_date: Mapped[datetime.date] = mapped_column(nullable=False, index=True)
    lead_days: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    fare_class: Mapped[str] = mapped_column(String(20), nullable=False, default="economy")
    passenger_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    base_fare: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    taxes: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    airport_charges: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    convenience_fee: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_fare: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    availability: Mapped[str] = mapped_column(
        String(30), default="available",
        nullable=False,
        comment="available | sold_out | limited"
    )
    raw_payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    quality_status: Mapped[str] = mapped_column(
        String(20), default="valid",
        nullable=False,
        index=True,
        comment="valid | invalid | missing | duplicate"
    )
    outlier_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    outlier_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duplicate_group_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[dt] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    source: Mapped["Source"] = relationship("Source", back_populates="observations")
    airline: Mapped["Airline"] = relationship("Airline", back_populates="observations")
    route: Mapped["Route"] = relationship("Route", back_populates="observations")


class RouteDailyPrice(Base):
    """
    Aggregated representative price for a route/lead_days on a given date.
    Calculated from valid fare observations.
    """
    __tablename__ = "route_daily_prices"
    __table_args__ = (
        UniqueConstraint("date", "route_id", "lead_days", name="uq_route_daily_price"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[datetime.date] = mapped_column(nullable=False, index=True)
    route_id: Mapped[int] = mapped_column(Integer, ForeignKey("routes.id"), nullable=False, index=True)
    lead_days: Mapped[int] = mapped_column(Integer, nullable=False)
    representative_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="Median valid fare")
    observation_count: Mapped[int] = mapped_column(Integer, default=0)
    valid_observation_count: Mapped[int] = mapped_column(Integer, default=0)
    missing_count: Mapped[int] = mapped_column(Integer, default=0)
    outlier_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[dt] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    route: Mapped["Route"] = relationship("Route", back_populates="daily_prices")


class RouteIndex(Base):
    """
    Price relative (index) for a route on a given date.
    RouteIndex = (current_price / base_price) × 100
    """
    __tablename__ = "route_indices"
    __table_args__ = (
        UniqueConstraint("date", "route_id", name="uq_route_index"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[datetime.date] = mapped_column(nullable=False, index=True)
    route_id: Mapped[int] = mapped_column(Integer, ForeignKey("routes.id"), nullable=False, index=True)
    base_price: Mapped[float] = mapped_column(Float, nullable=False, comment="Illustrative POC base price")
    current_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    route_index: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    route_weight: Mapped[float] = mapped_column(Float, nullable=False, comment="Illustrative POC weight")
    contribution: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[dt] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    route: Mapped["Route"] = relationship("Route", back_populates="indices")


class AirfareIndex(Base):
    """
    Overall Airfare Price Index (APIx) for a given date.
    Weighted arithmetic mean of route indices.

    DISCLAIMER: Illustrative POC methodology — not an official CPI index.
    """
    __tablename__ = "airfare_indices"
    __table_args__ = (
        UniqueConstraint("date", name="uq_airfare_index_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[datetime.date] = mapped_column(nullable=False, unique=True, index=True)
    index_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    daily_change_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    weekly_change_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    monthly_change_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    observation_count: Mapped[int] = mapped_column(Integer, default=0)
    coverage_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[dt] = mapped_column(DateTime(timezone=True), server_default=func.now())
