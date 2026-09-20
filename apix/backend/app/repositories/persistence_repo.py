"""Persistence repository functions for observations and index data."""
from datetime import date
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AirfareIndex,
    Airline,
    FareObservation,
    Route,
    RouteDailyPrice,
    RouteIndex,
    Source,
)


# ---------------------------------------------------------------------------
# Seed / ensure reference data
# ---------------------------------------------------------------------------

async def _ensure_source(db: AsyncSession, name: str, source_type: str) -> Source:
    result = await db.execute(select(Source).where(Source.name == name))
    src = result.scalar_one_or_none()
    if src is None:
        src = Source(name=name, source_type=source_type)
        db.add(src)
        await db.flush()
    return src


async def _ensure_airline(db: AsyncSession, code: str, name: str) -> Airline:
    result = await db.execute(select(Airline).where(Airline.code == code))
    airline = result.scalar_one_or_none()
    if airline is None:
        airline = Airline(code=code, name=name)
        db.add(airline)
        await db.flush()
    return airline


# ---------------------------------------------------------------------------
# persist_observations
# ---------------------------------------------------------------------------

async def persist_observations(
    db: AsyncSession,
    cleaned_obs: list,
    route_weights: dict,
) -> int:
    """Persist cleaned observations to the database. Returns count inserted."""
    # Ensure we have reference data
    source = await _ensure_source(db, "synthetic_mock", "ota_mock")

    # Build route map
    result = await db.execute(select(Route))
    routes = result.scalars().all()
    route_map: Dict[str, Route] = {r.route_code: r for r in routes}

    # Build airline map
    airline_cache: Dict[str, Airline] = {}

    count = 0
    for cleaned in cleaned_obs:
        raw_obs = cleaned.obs
        route_code = f"{raw_obs.origin}-{raw_obs.destination}"
        route = route_map.get(route_code)
        if route is None:
            continue

        airline_code = raw_obs.airline_code or "XX"
        if airline_code not in airline_cache:
            airline_cache[airline_code] = await _ensure_airline(
                db, airline_code, f"Airline {airline_code}"
            )
        airline = airline_cache[airline_code]

        fo = FareObservation(
            source_id=source.id,
            airline_id=airline.id,
            route_id=route.id,
            search_timestamp=raw_obs.search_timestamp,
            travel_date=raw_obs.travel_date,
            lead_days=raw_obs.lead_days,
            fare_class=raw_obs.fare_class,
            passenger_count=raw_obs.passenger_count,
            base_fare=raw_obs.base_fare,
            taxes=raw_obs.taxes,
            airport_charges=raw_obs.airport_charges,
            convenience_fee=raw_obs.convenience_fee,
            total_fare=raw_obs.total_fare,
            currency=raw_obs.currency,
            availability=raw_obs.availability,
            quality_status=cleaned.quality_status,
            outlier_flag=cleaned.outlier_flag,
            outlier_reason=cleaned.outlier_reason,
        )
        db.add(fo)
        count += 1

    await db.flush()
    return count


# ---------------------------------------------------------------------------
# get_observations_as_dicts
# ---------------------------------------------------------------------------

async def get_observations_as_dicts(db: AsyncSession) -> List[Dict[str, Any]]:
    stmt = (
        select(FareObservation, Route)
        .join(Route, FareObservation.route_id == Route.id)
    )
    result = await db.execute(stmt)
    rows = result.all()
    out = []
    for fo, route in rows:
        out.append(
            {
                "id": fo.id,
                "route_code": route.route_code,
                "travel_date": fo.travel_date,
                "lead_days": fo.lead_days,
                "total_fare": fo.total_fare,
                "quality_status": fo.quality_status,
                "outlier_flag": fo.outlier_flag,
                "availability": fo.availability,
            }
        )
    return out


# ---------------------------------------------------------------------------
# Upsert helpers
# ---------------------------------------------------------------------------

async def upsert_route_daily_price(
    db: AsyncSession,
    obs_date: date,
    route_id: int,
    lead_days: int,
    representative_price: Optional[float],
    observation_count: int,
    valid_observation_count: int,
    missing_count: int,
    outlier_count: int,
) -> None:
    stmt = (
        pg_insert(RouteDailyPrice)
        .values(
            date=obs_date,
            route_id=route_id,
            lead_days=lead_days,
            representative_price=representative_price,
            observation_count=observation_count,
            valid_observation_count=valid_observation_count,
            missing_count=missing_count,
            outlier_count=outlier_count,
        )
        .on_conflict_do_update(
            constraint="uq_route_daily_price",
            set_=dict(
                representative_price=representative_price,
                observation_count=observation_count,
                valid_observation_count=valid_observation_count,
                missing_count=missing_count,
                outlier_count=outlier_count,
            ),
        )
    )
    await db.execute(stmt)


async def upsert_route_index(
    db: AsyncSession,
    obs_date: date,
    route_id: int,
    base_price: float,
    current_price: Optional[float],
    route_index: Optional[float],
    route_weight: float,
    contribution: Optional[float],
) -> None:
    stmt = (
        pg_insert(RouteIndex)
        .values(
            date=obs_date,
            route_id=route_id,
            base_price=base_price,
            current_price=current_price,
            route_index=route_index,
            route_weight=route_weight,
            contribution=contribution,
        )
        .on_conflict_do_update(
            constraint="uq_route_index",
            set_=dict(
                base_price=base_price,
                current_price=current_price,
                route_index=route_index,
                route_weight=route_weight,
                contribution=contribution,
            ),
        )
    )
    await db.execute(stmt)


async def upsert_airfare_index(
    db: AsyncSession,
    obs_date: date,
    index_value: Optional[float],
    daily_change_pct: Optional[float],
    weekly_change_pct: Optional[float],
    monthly_change_pct: Optional[float],
    observation_count: int,
    coverage_pct: Optional[float],
) -> None:
    stmt = (
        pg_insert(AirfareIndex)
        .values(
            date=obs_date,
            index_value=index_value,
            daily_change_pct=daily_change_pct,
            weekly_change_pct=weekly_change_pct,
            monthly_change_pct=monthly_change_pct,
            observation_count=observation_count,
            coverage_pct=coverage_pct,
        )
        .on_conflict_do_update(
            index_elements=["date"],
            set_=dict(
                index_value=index_value,
                daily_change_pct=daily_change_pct,
                weekly_change_pct=weekly_change_pct,
                monthly_change_pct=monthly_change_pct,
                observation_count=observation_count,
                coverage_pct=coverage_pct,
            ),
        )
    )
    await db.execute(stmt)
