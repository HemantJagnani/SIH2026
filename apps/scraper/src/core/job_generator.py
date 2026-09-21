"""
Job Generator for the India Airfare Index.

Spec Phase 10 (§33):
Generates the cross-product of:
    Routes × Lead Times × Sources

Produces a list of FareSearchRequest parameters to be mapped in Airflow.
"""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

from adapters.models import FareSearchRequest, CollectionMode
from models.enums import CabinClass, TripType


class JobGenerator:
    """
    Reads configuration files and generates scraping jobs.
    """

    def __init__(self, config_dir: str | Path | None = None):
        if config_dir is None:
            # Default to project root / config
            base_path = Path(__file__).resolve().parent.parent.parent.parent.parent
            self.config_dir = base_path / "config"
        else:
            self.config_dir = Path(config_dir)

    def load_yaml(self, filename: str) -> Any:
        path = self.config_dir / filename
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def generate_jobs(
        self,
        collection_date: date | None = None,
        passenger_count: int = 1,
        cabin: CabinClass = CabinClass.ECONOMY,
        trip_type: TripType = TripType.ONE_WAY,
    ) -> list[dict]:
        """
        Generate dictionaries representing FareSearchRequests.
        We return dicts instead of FareSearchRequest objects directly because
        Airflow needs serializable data for dynamic task mapping (XCom).

        Args:
            collection_date: The date the collection is occurring (defaults to today).
            passenger_count: Number of passengers.
            cabin: Cabin class.
            trip_type: Trip type.

        Returns:
            List of dictionaries that can be unpacked into FareSearchRequest(**kwargs).
        """
        if collection_date is None:
            collection_date = datetime.now(timezone.utc).date()

        routes_data = self.load_yaml("routes.yaml")
        lead_times_data = self.load_yaml("lead_times.yaml")
        sources_data = self.load_yaml("sources.yaml")

        routes = routes_data.get("routes", [])
        lead_times = lead_times_data.get("lead_times", [])
        sources = sources_data.get("sources", [])

        jobs = []

        for source in sources:
            source_name = source["name"]
            permitted_method = source.get("permitted_method", "web")
            
            # Map configuration method to CollectionMode enum value
            mode = CollectionMode.API if permitted_method == "api" else CollectionMode.BROWSER

            for route in routes:
                origin = route["origin"]
                destination = route["destination"]

                for lead_days in lead_times:
                    travel_date = collection_date + timedelta(days=lead_days)

                    job = {
                        "source": source_name,
                        "origin": origin,
                        "destination": destination,
                        "travel_date": travel_date.isoformat(),
                        "lead_days": lead_days,
                        "trip_type": trip_type.value,
                        "cabin": cabin.value,
                        "adults": passenger_count,
                        "children": 0,
                        "infants": 0,
                        "currency": "INR",
                        "collection_mode": mode.value,
                    }
                    jobs.append(job)

        return jobs
