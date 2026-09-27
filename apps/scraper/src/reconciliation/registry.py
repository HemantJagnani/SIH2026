"""
Source Registry & Configuration Mechanism for APIx Cross-Source Scraping.
Implements §3 and §4 of the APIx Cross-Source Specification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Type

from .models import PriceSemantics


@dataclass
class SourceConfig:
    """Configuration and capability metadata for a registered fare source per §4."""
    source_id: str
    source_name: str
    supported_fields: Set[str]
    extraction_mode: str = "CORE_ONLY"
    default_price_semantics: PriceSemantics = PriceSemantics.DISPLAYED_TOTAL
    enabled: bool = True
    source_status: str = "ACTIVE"  # ACTIVE, EXPERIMENTAL, DEPRECATED, DISABLED
    adapter_class_name: Optional[str] = None


class SourceRegistry:
    """
    Central registry for all active, experimental, and future fare data sources.
    Enforces generic adapter resolution without modifying core reconciliation logic.
    """
    _instance: Optional[SourceRegistry] = None

    def __init__(self):
        self._sources: Dict[str, SourceConfig] = {}
        self._initialize_built_in_sources()

    @classmethod
    def get_registry(cls) -> SourceRegistry:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _initialize_built_in_sources(self):
        """Registers the standard primary sources: Google Flights, EaseMyTrip, Ixigo."""
        # 1. Google Flights
        self.register_source(
            SourceConfig(
                source_id="google_flights",
                source_name="Google Flights",
                supported_fields={
                    "route", "origin", "destination", "travel_date", "lead_time",
                    "airline", "flight_number", "departure_time", "arrival_time",
                    "stops", "cabin", "total_fare", "currency"
                },
                extraction_mode="CORE_ONLY",
                default_price_semantics=PriceSemantics.DISPLAYED_TOTAL,
                enabled=True,
                source_status="ACTIVE",
                adapter_class_name="GoogleFlightsReconciliationAdapter",
            )
        )
        
        # 2. EaseMyTrip
        self.register_source(
            SourceConfig(
                source_id="easemytrip",
                source_name="EaseMyTrip",
                supported_fields={
                    "route", "origin", "destination", "travel_date", "lead_time",
                    "airline", "flight_number", "departure_time", "arrival_time",
                    "stops", "cabin", "fare_family", "baggage", "cabin_baggage_kg",
                    "checkin_baggage_kg", "refundability", "changeability",
                    "total_fare", "currency"
                },
                extraction_mode="CORE_ONLY",
                default_price_semantics=PriceSemantics.DISPLAYED_TOTAL,
                enabled=True,
                source_status="ACTIVE",
                adapter_class_name="EaseMyTripReconciliationAdapter",
            )
        )

        # 3. Ixigo
        self.register_source(
            SourceConfig(
                source_id="ixigo",
                source_name="Ixigo",
                supported_fields={
                    "route", "origin", "destination", "travel_date", "lead_time",
                    "airline", "flight_number", "departure_time", "arrival_time",
                    "stops", "cabin", "fare_family", "baggage", "total_fare", "currency"
                },
                extraction_mode="CORE_ONLY",
                default_price_semantics=PriceSemantics.DISPLAYED_TOTAL,
                enabled=True,
                source_status="ACTIVE",
                adapter_class_name="IxigoReconciliationAdapter",
            )
        )

    def register_source(self, config: SourceConfig) -> None:
        """Register a new or custom source dynamically."""
        self._sources[config.source_id.lower()] = config

    def get_source(self, source_id: str) -> Optional[SourceConfig]:
        """Lookup source configuration by ID."""
        return self._sources.get(source_id.lower())

    def list_sources(self, enabled_only: bool = False) -> List[SourceConfig]:
        """List all registered sources."""
        sources = list(self._sources.values())
        if enabled_only:
            return [s for s in sources if s.enabled and s.source_status == "ACTIVE"]
        return sources

    def is_enabled(self, source_id: str) -> bool:
        """Check if source is enabled and active."""
        src = self.get_source(source_id)
        return src is not None and src.enabled and src.source_status == "ACTIVE"
