"""
Synthetic fare source – generates plausible, deterministic fares.

Used by `scripts/seed_synthetic.py` to populate 60 days of history
before real data exists (for demos and the validation story).

Price model:
  - Base fare per route
  - Lead-time curve: fares rise as departure nears (sigmoid shape)
  - Weekly pattern: Mon/Fri more expensive, Tue/Wed cheaper
  - Festival spike: ±10% around festival dates
  - White noise: ~3% std
  - Rare sold-out slots (~5% of flights)
  - Random missing quotes (~3% of flights)

All rows get `is_synthetic = True`.
"""
from __future__ import annotations

import math
import random
from datetime import date, datetime, timedelta

from apix.models import Quote, RawSnapshot
from apix.sources.base import FareSource

# Base fares (₹) per route before adjustments
_BASE_FARES: dict[str, float] = {
    "DEL-BOM": 5200.0,
    "DEL-BLR": 6000.0,
    "BOM-BLR": 3800.0,
}

# Sample carrier pool with realistic flight numbers
_CARRIERS: list[dict] = [
    {"carrier": "IndiGo",   "prefix": "6E", "numbers": [101, 102, 201, 202]},
    {"carrier": "Air India","prefix": "AI", "numbers": [611, 612, 815, 816]},
    {"carrier": "SpiceJet", "prefix": "SG", "numbers": [112, 113, 224, 225]},
    {"carrier": "Vistara",  "prefix": "UK", "numbers": [835, 836, 927, 928]},
]

# Departure times bucketed by band
_DEP_TIMES = {
    "morning":   ["06:00", "07:30", "08:45", "10:15", "11:00"],
    "afternoon": ["12:30", "13:45", "15:00", "16:30", "17:45"],
    "evening":   ["18:30", "19:45", "20:15", "21:30", "22:00"],
}

# Festival dates (approximate) for 2026 spike
_FESTIVAL_DATES = {
    date(2026, 10, 2),   # Gandhi Jayanti
    date(2026, 10, 23),  # Dussehra approx
    date(2026, 11, 1),   # Diwali approx
    date(2026, 11, 2),
    date(2026, 11, 3),
    date(2026, 12, 25),  # Christmas
}


def _lead_curve_multiplier(lead_days: int) -> float:
    """Sigmoid curve: fares rise steeply as departure nears."""
    # Ranges from ~0.75 at 30 days to ~1.55 at 1 day
    x = (30 - lead_days) / 10.0
    return 0.75 + 0.80 / (1 + math.exp(-x))


def _weekday_multiplier(travel_date: date) -> float:
    """Mon/Fri +8%, Tue/Wed -5%, others neutral."""
    wd = travel_date.weekday()  # 0=Mon
    if wd in (0, 4):    # Monday, Friday
        return 1.08
    if wd in (1, 2):    # Tuesday, Wednesday
        return 0.95
    return 1.0


def _festival_multiplier(travel_date: date, window: int = 3) -> float:
    """Return 1.12 if travel_date is within `window` days of a festival."""
    for f in _FESTIVAL_DATES:
        if abs((travel_date - f).days) <= window:
            return 1.12
    return 1.0


def _generate_fares(
    route: str,
    travel_date: date,
    lead_days: int,
    rng: random.Random,
) -> list[dict]:
    """Generate a list of raw fare dicts for one (route, travel_date)."""
    base = _BASE_FARES.get(route, 5000.0)
    price_adj = (
        base
        * _lead_curve_multiplier(lead_days)
        * _weekday_multiplier(travel_date)
        * _festival_multiplier(travel_date)
    )

    fares = []
    for band, times in _DEP_TIMES.items():
        for dep_time in times:
            # ~3% chance of a missing quote (not collected)
            if rng.random() < 0.03:
                continue

            # Pick a random carrier
            carrier_info = rng.choice(_CARRIERS)
            flight_no = f"{carrier_info['prefix']}-{rng.choice(carrier_info['numbers'])}"

            # ~5% sold out
            sold_out = rng.random() < 0.05

            # Add carrier spread + noise
            carrier_spread = rng.uniform(-0.08, 0.12)
            noise = rng.gauss(0, 0.03)
            total = round(price_adj * (1 + carrier_spread + noise), -1)  # round to nearest 10
            total = max(total, 1500.0)

            # Taxes: ~18-20% of total
            taxes = round(total * rng.uniform(0.18, 0.20), -1)
            base_fare = round(total - taxes, -1)

            fares.append({
                "carrier": carrier_info["carrier"],
                "flight_no": flight_no,
                "dep_time": dep_time,
                "dep_band": band,
                "stops": 0,
                "fare_class": "economy",
                "base_fare": base_fare if rng.random() > 0.05 else None,  # 5% total-only
                "taxes": taxes if rng.random() > 0.05 else None,
                "total_fare": None if sold_out else total,
                "sold_out": sold_out,
            })

    return fares


class SyntheticSource(FareSource):
    """
    Generates deterministic synthetic fares.

    Pass a fixed `seed` (default 42) to get reproducible output.
    The known true price path is stored in `self.true_prices` after fetch,
    keyed by (route, lead_days, dep_band) → {obs_date: min_fare}.
    """

    def __init__(self, run_id: int, seed: int = 42) -> None:
        self.run_id = run_id
        self._rng = random.Random(seed)
        self.true_prices: dict[tuple, dict[date, float]] = {}

    def fetch(
        self,
        route: str,
        origin: str,
        destination: str,
        travel_date: date,
        run_id: int,
    ) -> tuple[list[Quote], RawSnapshot]:
        obs_date = datetime.utcnow().date()
        lead = (travel_date - obs_date).days
        if lead < 0:
            lead = 0

        raw_fares = _generate_fares(route, travel_date, lead, self._rng)

        snapshot = RawSnapshot(
            run_id=run_id,
            route=route,
            travel_date=travel_date,
            fetched_at=datetime.utcnow(),
            url=f"synthetic://{route}/{travel_date}",
            http_status=200,
            robots_allowed=True,
            body_path=None,
        )

        quotes: list[Quote] = []
        for raw in raw_fares:
            q = Quote(
                run_id=run_id,
                obs_date=obs_date,
                source="synthetic",
                route=route,
                origin=origin,
                destination=destination,
                travel_date=travel_date,
                lead_days=lead,
                carrier=raw["carrier"],
                flight_no=raw["flight_no"],
                dep_time=raw["dep_time"],
                dep_band=raw["dep_band"],
                stops=raw["stops"],
                fare_class=raw["fare_class"],
                base_fare=raw["base_fare"],
                taxes=raw["taxes"],
                total_fare=raw["total_fare"],
                sold_out=raw["sold_out"],
                parse_ok=True,
                anomaly_flag=False,
                is_synthetic=True,
            )
            quotes.append(q)

        # Record true minimum prices for test validation
        from itertools import groupby
        key_fn = lambda q: q.dep_band
        eligible = [
            q for q in quotes
            if not q.sold_out and q.total_fare is not None
        ]
        for band, group in groupby(sorted(eligible, key=key_fn), key=key_fn):
            group_list = list(group)
            if group_list:
                min_fare = min(q.total_fare for q in group_list)
                cell = (route, lead, band)
                if cell not in self.true_prices:
                    self.true_prices[cell] = {}
                self.true_prices[cell][obs_date] = min_fare

        return quotes, snapshot
