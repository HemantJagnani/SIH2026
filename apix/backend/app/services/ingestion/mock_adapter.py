"""
Curated Synthetic Fare Dataset — APIx POC.

Generates a realistic 90-day dataset (June–Sept 2026) with:
  - Summer travel surge (June–July): fares climb ~15–20%
  - Mid-August plateau (school season): fares stabilise
  - Festive season ramp (Sept, ahead of Navratri/Dussehra): fares spike ~25–30%
  - Weekend micro-surges (Friday/Saturday bookings)
  - Lead-time realism: last-minute (T+1) fares are ~70% more than advance (T+30)
  - Intentional anomalies for quality-pipeline demonstration

DISCLAIMER: Fully synthetic data for POC purposes. Not real market data.
"""
from __future__ import annotations

import math
import random
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from app.services.ingestion.source_adapter import RawFareObservation

# ─────────────────────────────────────────────────────────────────────────────
# Route configuration
# ─────────────────────────────────────────────────────────────────────────────

ROUTES = [
    ("DEL", "BOM"),
    ("DEL", "BLR"),
    ("BOM", "BLR"),
]

AIRLINES = ["6E", "AI"]
AIRLINE_NAMES = {"6E": "IndiGo", "AI": "Air India"}

LEAD_TIMES = [1, 7, 30]

# Illustrative base fares per route/lead-time (INR, synthetic POC values)
# These represent a "normal" off-peak day at each lead time
BASE_FARES: dict[tuple[str, str], dict[int, float]] = {
    ("DEL", "BOM"): {1: 9200,  7: 6500,  30: 5000},
    ("DEL", "BLR"): {1: 8500,  7: 6000,  30: 4700},
    ("BOM", "BLR"): {1: 7800,  7: 5500,  30: 4200},
}

TAX_RATE = 0.18
AIRPORT_CHARGE = 300.0
CONVENIENCE_FEE = 150.0


# ─────────────────────────────────────────────────────────────────────────────
# Trend model — returns a day-level price multiplier
# ─────────────────────────────────────────────────────────────────────────────

def _trend_multiplier(search_date: date, base_date: date) -> float:
    """
    Returns a price multiplier for the given search date.

    Trend shape (illustrative):
      - Day 0–14  (early Jun): gentle ramp up from 1.00 → 1.10 (summer onset)
      - Day 14–44 (Jun–Jul):  summer peak, plateau around 1.15–1.20
      - Day 44–60 (Aug):      slight correction, fares ease to ~1.08
      - Day 60–90 (Sept):     festive pre-booking surge → 1.20–1.30
    """
    day = (search_date - base_date).days

    if day < 0:
        return 1.0

    # Base sinusoidal seasonal trend
    seasonal = 1.10 + 0.10 * math.sin(math.pi * day / 45)

    # Festive ramp from day 60 onwards (Sept festive season)
    if day >= 60:
        festive_ramp = 0.003 * (day - 60)  # ~+0.9% per day
        seasonal += festive_ramp

    # Clamp to reasonable range
    return max(0.85, min(seasonal, 1.35))


def _weekend_multiplier(d: date) -> float:
    """Weekends (Fri=4, Sat=5) carry a small booking premium."""
    if d.weekday() in (4, 5):
        return 1.06
    return 1.0


def _generate_obs(
    rng: random.Random,
    origin: str,
    destination: str,
    travel_date: date,
    lead_days: int,
    airline_code: str,
    source_label: str,
    price_multiplier: float,
) -> RawFareObservation:
    base_fare_center = BASE_FARES[(origin, destination)][lead_days]

    # Air India slightly premium
    if airline_code == "AI":
        base_fare_center *= 1.03

    # OTA adds convenience fee but may offer marginal discount on base
    ota_factor = rng.uniform(0.98, 1.02) if source_label == "ota_mock" else 1.0

    # Add ±5% noise per observation
    noise = rng.uniform(0.95, 1.05)

    base_fare = round(base_fare_center * price_multiplier * ota_factor * noise, 2)
    taxes = round(base_fare * TAX_RATE, 2)
    airport_charges = AIRPORT_CHARGE
    convenience_fee = CONVENIENCE_FEE if source_label == "ota_mock" else 0.0
    total_fare = round(base_fare + taxes + airport_charges + convenience_fee, 2)

    return RawFareObservation(
        source_name=source_label,
        airline_code=airline_code,
        origin=origin,
        destination=destination,
        search_timestamp=datetime.now(timezone.utc),
        travel_date=travel_date,
        lead_days=lead_days,
        fare_class="economy",
        passenger_count=1,
        base_fare=base_fare,
        taxes=taxes,
        airport_charges=airport_charges,
        convenience_fee=convenience_fee,
        total_fare=total_fare,
        currency="INR",
        availability="available",
        raw_payload={
            "source_label": source_label,
            "airline_name": AIRLINE_NAMES.get(airline_code, airline_code),
            "synthetic": True,
        },
    )


def generate_curated_dataset(
    start_date: date,
    num_days: int = 90,
    seed: int = 42,
) -> list[RawFareObservation]:
    """
    Generate a 90-day curated synthetic fare dataset with realistic trends.

    Covers:
      - Summer travel surge (days 0–44)
      - August stabilisation (days 44–60)
      - Festive season ramp-up (days 60–90)

    Anomalies injected for quality pipeline demonstration:
      - ~1.5% missing prices
      - ~1% sold-out
      - ~0.5% extreme outliers
      - ~1.5% duplicates
    """
    rng = random.Random(seed)
    observations: list[RawFareObservation] = []

    for day_offset in range(num_days):
        search_date = start_date + timedelta(days=day_offset)
        trend = _trend_multiplier(search_date, start_date)
        weekend = _weekend_multiplier(search_date)

        for origin, destination in ROUTES:
            for lead_days in LEAD_TIMES:
                travel_date = search_date + timedelta(days=lead_days)

                for airline_code in AIRLINES:
                    price_mult = trend * weekend

                    # Airline direct
                    obs = _generate_obs(
                        rng, origin, destination, travel_date,
                        lead_days, airline_code, "airline_direct", price_mult,
                    )
                    observations.append(obs)

                    # OTA source
                    ota_obs = _generate_obs(
                        rng, origin, destination, travel_date,
                        lead_days, airline_code, "ota_mock", price_mult,
                    )
                    observations.append(ota_obs)

    total = len(observations)

    # ── Inject anomalies ──────────────────────────────────────────────────────

    # Missing prices (~1.5%)
    missing_count = max(5, int(total * 0.015))
    for idx in rng.sample(range(total), missing_count):
        obs = observations[idx]
        observations[idx] = RawFareObservation(
            source_name=obs.source_name, airline_code=obs.airline_code,
            origin=obs.origin, destination=obs.destination,
            search_timestamp=obs.search_timestamp, travel_date=obs.travel_date,
            lead_days=obs.lead_days, fare_class=obs.fare_class,
            passenger_count=obs.passenger_count,
            base_fare=None, taxes=None, airport_charges=None,
            convenience_fee=None, total_fare=None,
            currency="INR", availability="available",
            raw_payload={**obs.raw_payload, "anomaly": "missing_price"},
        )

    # Sold-out (~1%)
    sold_out_pool = [i for i in range(total) if observations[i].total_fare is not None]
    for idx in rng.sample(sold_out_pool, max(3, int(total * 0.01))):
        obs = observations[idx]
        observations[idx] = RawFareObservation(
            source_name=obs.source_name, airline_code=obs.airline_code,
            origin=obs.origin, destination=obs.destination,
            search_timestamp=obs.search_timestamp, travel_date=obs.travel_date,
            lead_days=obs.lead_days, fare_class=obs.fare_class,
            passenger_count=obs.passenger_count,
            base_fare=None, taxes=None, airport_charges=None,
            convenience_fee=None, total_fare=None,
            currency="INR", availability="sold_out",
            raw_payload={**obs.raw_payload, "anomaly": "sold_out"},
        )

    # Extreme outliers (~0.5%) — 5× price, flagged by cleaning pipeline
    valid_pool = [i for i in range(total) if observations[i].total_fare is not None]
    for idx in rng.sample(valid_pool, max(2, int(total * 0.005))):
        obs = observations[idx]
        extreme = round((obs.total_fare or 10000) * 5.5, 2)
        observations[idx] = RawFareObservation(
            source_name=obs.source_name, airline_code=obs.airline_code,
            origin=obs.origin, destination=obs.destination,
            search_timestamp=obs.search_timestamp, travel_date=obs.travel_date,
            lead_days=obs.lead_days, fare_class=obs.fare_class,
            passenger_count=obs.passenger_count,
            base_fare=round(extreme * 0.7, 2), taxes=round(extreme * 0.2, 2),
            airport_charges=AIRPORT_CHARGE, convenience_fee=0.0,
            total_fare=extreme, currency="INR", availability="available",
            raw_payload={**obs.raw_payload, "anomaly": "extreme_outlier"},
        )

    # Duplicates (~1.5%)
    dup_pool = [i for i in range(total) if observations[i].total_fare is not None]
    for idx in rng.sample(dup_pool, max(4, int(total * 0.015))):
        observations.append(RawFareObservation(**observations[idx].__dict__))

    return observations


# Keep backwards-compatible alias for anything that imports the old name
def generate_synthetic_dataset(
    start_date: date,
    num_days: int = 90,
    seed: int = 42,
) -> list[RawFareObservation]:
    return generate_curated_dataset(start_date, num_days, seed)
