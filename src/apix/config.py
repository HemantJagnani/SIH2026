"""
Typed configuration loader for APIx.

Loads config.yaml, validates that all weight sets sum to 1.0,
and exposes frozen dataclasses for use throughout the pipeline.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml

_CONFIG_PATH = Path(__file__).parent.parent.parent / "config.yaml"
_WEIGHT_TOLERANCE = 1e-6


@dataclass(frozen=True)
class RouteConfig:
    id: str
    origin: str
    destination: str
    weight: float


@dataclass(frozen=True)
class LeadDayConfig:
    days: int
    weight: float


@dataclass(frozen=True)
class ScheduleConfig:
    hour: int
    minute: int


@dataclass(frozen=True)
class SourceConfig:
    name: Literal["fixture", "live", "synthetic"]
    user_agent: str
    min_delay_s: int
    max_delay_s: int


@dataclass(frozen=True)
class DepartureBands:
    morning: tuple[str, str]
    afternoon: tuple[str, str]
    evening: tuple[str, str]


@dataclass(frozen=True)
class ItemRules:
    fare_class: str
    nonstop_only: bool
    price_statistic: Literal["min", "median"]
    exclude_anomalies: bool


@dataclass(frozen=True)
class IndexConfig:
    base_value: float
    min_coverage: float


@dataclass(frozen=True)
class AppConfig:
    timezone: str
    schedule: ScheduleConfig
    source: SourceConfig
    routes: tuple[RouteConfig, ...]
    lead_days: tuple[LeadDayConfig, ...]
    departure_bands: DepartureBands
    item_rules: ItemRules
    index: IndexConfig


def _validate_weights(items: list, label: str) -> None:
    """Raise ValueError if weights do not sum to 1 within tolerance."""
    total = sum(item["weight"] for item in items)
    if not math.isclose(total, 1.0, abs_tol=_WEIGHT_TOLERANCE):
        raise ValueError(
            f"{label} weights must sum to 1.0 (got {total:.6f}). "
            f"Adjust the weights in config.yaml."
        )


def load_config(path: Path | None = None) -> AppConfig:
    """Load and validate the YAML config file, returning an AppConfig."""
    config_path = path or _CONFIG_PATH
    with open(config_path, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    # Validate weights
    _validate_weights(raw["routes"], "routes")
    _validate_weights(raw["lead_days"], "lead_days")

    routes = tuple(
        RouteConfig(
            id=r["id"],
            origin=r["origin"],
            destination=r["destination"],
            weight=float(r["weight"]),
        )
        for r in raw["routes"]
    )

    lead_days = tuple(
        LeadDayConfig(days=int(ld["days"]), weight=float(ld["weight"]))
        for ld in raw["lead_days"]
    )

    db_raw = raw["departure_bands"]
    departure_bands = DepartureBands(
        morning=tuple(db_raw["morning"]),
        afternoon=tuple(db_raw["afternoon"]),
        evening=tuple(db_raw["evening"]),
    )

    sched = raw["schedule"]
    ir = raw["item_rules"]
    idx = raw["index"]
    src = raw["source"]

    return AppConfig(
        timezone=raw["timezone"],
        schedule=ScheduleConfig(hour=sched["hour"], minute=sched["minute"]),
        source=SourceConfig(
            name=src["name"],
            user_agent=src["user_agent"],
            min_delay_s=int(src["min_delay_s"]),
            max_delay_s=int(src["max_delay_s"]),
        ),
        routes=routes,
        lead_days=lead_days,
        departure_bands=departure_bands,
        item_rules=ItemRules(
            fare_class=ir["fare_class"],
            nonstop_only=bool(ir["nonstop_only"]),
            price_statistic=ir["price_statistic"],
            exclude_anomalies=bool(ir["exclude_anomalies"]),
        ),
        index=IndexConfig(
            base_value=float(idx["base_value"]),
            min_coverage=float(idx["min_coverage"]),
        ),
    )
