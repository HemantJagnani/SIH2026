"""
Fixture source – replays saved JSON files from tests/fixtures/.

This is the **default** source so the full pipeline can run with
no network access at all. Each fixture file is a JSON array of
route-level objects, each with a list of quote dicts.

Fixture file format: tests/fixtures/fares_sample.json
"""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from apix.models import Quote, RawSnapshot
from apix.sources.base import FareSource

_FIXTURES_DIR = Path(__file__).parent.parent.parent.parent / "tests" / "fixtures"
_DEFAULT_FIXTURE = "fares_sample.json"


class FixtureSource(FareSource):
    """
    Replays quotes from a saved JSON fixture file.

    The fixture is route-agnostic: every route gets the quotes from
    the matching entry in the fixture array (matched by route id).
    If no match is found for a route, an empty list is returned.
    """

    def __init__(
        self,
        run_id: int,
        fixture_path: Path | None = None,
        user_agent: str = "APIx-Prototype/0.1",
    ) -> None:
        self.run_id = run_id
        self.user_agent = user_agent
        fixture_path = fixture_path or (_FIXTURES_DIR / _DEFAULT_FIXTURE)
        with open(fixture_path, encoding="utf-8") as fh:
            self._data: list[dict] = json.load(fh)

    def fetch(
        self,
        route: str,
        origin: str,
        destination: str,
        travel_date: date,
        run_id: int,
    ) -> tuple[list[Quote], RawSnapshot]:
        now = datetime.utcnow()
        snapshot = RawSnapshot(
            run_id=run_id,
            route=route,
            travel_date=travel_date,
            fetched_at=now,
            url=f"fixture://{route}/{travel_date}",
            http_status=200,
            robots_allowed=True,
            body_path=None,
        )

        # Find the matching route block in the fixture
        route_block = next(
            (b for b in self._data if b.get("route") == route),
            None,
        )
        if route_block is None:
            return [], snapshot

        quotes = []
        obs_date = now.date()
        lead = (travel_date - obs_date).days

        for raw in route_block.get("quotes", []):
            q = Quote(
                run_id=run_id,
                obs_date=obs_date,
                source="fixture",
                route=route,
                origin=origin,
                destination=destination,
                travel_date=travel_date,
                lead_days=lead,
                carrier=raw.get("carrier", ""),
                flight_no=raw.get("flight_no"),
                dep_time=raw.get("dep_time"),
                dep_band=None,  # assigned by clean.py
                stops=int(raw.get("stops", 0)),
                fare_class=raw.get("fare_class", "economy"),
                base_fare=raw.get("base_fare"),
                taxes=raw.get("taxes"),
                total_fare=raw.get("total_fare"),
                sold_out=bool(raw.get("sold_out", False)),
                parse_ok=True,
                anomaly_flag=False,
                is_synthetic=False,
            )
            quotes.append(q)

        return quotes, snapshot
