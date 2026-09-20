"""
Domain model dataclasses for APIx.

Quote        – one fare quote from a source (parsed from a page)
RawSnapshot  – the raw HTTP response saved alongside each run
Item         – an aggregated (route, lead_days, dep_band) price for one day
IndexPoint   – one day's index level (overall or per-route)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal


@dataclass
class Quote:
    """A single airfare quote as returned by a FareSource."""
    # Observation metadata
    run_id: int
    obs_date: date
    source: str                       # fixture | live | synthetic

    # Route
    route: str                        # e.g. DEL-BOM
    origin: str
    destination: str
    travel_date: date
    lead_days: int                    # travel_date - obs_date

    # Flight details
    carrier: str
    flight_no: str | None
    dep_time: str | None              # HH:MM local 24 h
    dep_band: Literal["morning", "afternoon", "evening"] | None
    stops: int = 0
    fare_class: str = "economy"

    # Pricing
    base_fare: float | None = None    # null if site only shows total
    taxes: float | None = None
    total_fare: float | None = None

    # Flags
    sold_out: bool = False
    parse_ok: bool = True
    anomaly_flag: bool = False
    is_synthetic: bool = False

    # DB surrogate (set after insert)
    id: int | None = None


@dataclass
class RawSnapshot:
    """The raw HTTP response saved for audit and re-parsing."""
    run_id: int
    route: str
    travel_date: date
    fetched_at: datetime
    url: str
    http_status: int | None
    robots_allowed: bool
    body_path: str | None             # path relative to project root

    id: int | None = None


@dataclass
class Item:
    """Aggregated item price: the price_statistic of eligible quotes in one cell."""
    obs_date: date
    route: str
    lead_days: int
    dep_band: str
    price: float
    n_quotes: int
    is_synthetic: bool = False


@dataclass
class ItemRelative:
    """Ratio of consecutive item prices."""
    obs_date: date
    prev_obs_date: date
    route: str
    lead_days: int
    dep_band: str
    relative: float
    is_synthetic: bool = False


@dataclass
class IndexPoint:
    """One observation of the chained price index."""
    obs_date: date
    scope: Literal["overall", "route"]
    route: str | None                 # null for overall
    level: float | None               # null when low_coverage
    coverage: float
    low_coverage: bool
    gap_days: int = 0
    is_synthetic: bool = False
