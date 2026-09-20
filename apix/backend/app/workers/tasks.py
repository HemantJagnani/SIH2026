"""
APIx pipeline — async data ingestion and index calculation.

Steps:
  1. generate_observations → synthetic fare data
  2. clean_observations    → quality flags
  3. persist to DB         → FareObservation records
  4. calculate_route_prices→ RouteDailyPrice records
  5. calculate_route_indices→ RouteIndex records
  6. calculate_airfare_index→ AirfareIndex record
"""
from __future__ import annotations

import structlog
from datetime import date, timedelta
from typing import Optional

from app.core.config import settings

logger = structlog.get_logger(__name__)


async def _run_pipeline_async(
    num_days: Optional[int],
    seed: Optional[int],
    task_id: str,
) -> dict:
    from app.db.session import AsyncSessionLocal
    from app.services.ingestion.mock_adapter import generate_synthetic_dataset
    from app.services.cleaning.pipeline import clean_observations
    from app.repositories import (
        get_all_routes,
        persist_observations,
        upsert_route_daily_price,
        upsert_route_index,
        upsert_airfare_index,
        get_observations_as_dicts,
        get_latest_airfare_index,
        get_airfare_index_history,
        get_route_by_code,
    )
    from app.services.index_engine.calculator import (
        calculate_airfare_index,
        calculate_daily_change,
        calculate_median_fare,
        calculate_route_index,
        calculate_route_price,
    )

    _num_days = num_days or settings.SYNTHETIC_DAYS
    _seed = seed or settings.RANDOM_SEED
    base_date = settings.BASE_DATE

    logger.info("ingestion_started", days=_num_days, seed=_seed)

    # ── Step 1: Generate synthetic data ──────────────────────────────────────
    raw_observations = generate_synthetic_dataset(
        start_date=base_date,
        num_days=_num_days,
        seed=_seed,
    )
    logger.info("observations_collected", count=len(raw_observations))

    # ── Step 2: Clean observations ────────────────────────────────────────────
    cleaning_results = clean_observations(raw_observations)
    valid_count = sum(1 for r in cleaning_results if r.quality_status == "valid")
    invalid_count = sum(1 for r in cleaning_results if r.quality_status == "invalid")
    outlier_count = sum(1 for r in cleaning_results if r.outlier_flag)
    logger.info(
        "observations_cleaned",
        total=len(cleaning_results),
        valid=valid_count,
        invalid=invalid_count,
        outliers=outlier_count,
    )

    async with AsyncSessionLocal() as db:
        # ── Step 3: Persist to DB ─────────────────────────────────────────────
        persisted = await persist_observations(db, cleaning_results, settings.ROUTE_WEIGHTS)
        await db.commit()
        logger.info("observations_persisted", count=persisted)

        # ── Steps 4-6: Compute route prices and indices per day ───────────────
        logger.info("index_calculation_started")

        routes = await get_all_routes(db)
        route_map = {r.route_code: r for r in routes}

        # Fetch all observations once — filter per day inside the loop
        all_obs = await get_observations_as_dicts(db)
        valid_obs_count = sum(1 for o in all_obs if o["quality_status"] == "valid")

        for day_offset in range(_num_days):
            calc_date = base_date + timedelta(days=day_offset)

            route_indices_for_day: dict[str, float | None] = {}

            for route_code, route in route_map.items():
                # Lead-time medians — only observations for THIS day's travel dates
                lead_time_fares: dict[int, float | None] = {}
                for lt in settings.LEAD_TIME_WEIGHTS:
                    expected_travel_date = calc_date + timedelta(days=lt)
                    fares = [
                        o["total_fare"] for o in all_obs
                        if (
                            o["route_code"] == route_code
                            and o["lead_days"] == lt
                            and o["travel_date"] == expected_travel_date
                            and o["quality_status"] == "valid"
                            and not o["outlier_flag"]
                            and o["total_fare"] is not None
                        )
                    ]
                    median_fare = calculate_median_fare(fares) if fares else None
                    lead_time_fares[lt] = median_fare

                    # Upsert RouteDailyPrice
                    all_fares_for_lt = [
                        o["total_fare"] for o in all_obs
                        if (
                            o["route_code"] == route_code
                            and o["lead_days"] == lt
                            and o["travel_date"] == expected_travel_date
                        )
                    ]
                    valid_count_lt = len([f for f in fares if f is not None])
                    await upsert_route_daily_price(
                        db,
                        obs_date=calc_date,
                        route_id=route.id,
                        lead_days=lt,
                        representative_price=median_fare,
                        observation_count=len(all_fares_for_lt),
                        valid_observation_count=valid_count_lt,
                        missing_count=0,
                        outlier_count=0,
                    )

                current_price = calculate_route_price(lead_time_fares, settings.LEAD_TIME_WEIGHTS)
                base_price = settings.BASE_PRICES.get(route_code, 6000.0)
                route_index = calculate_route_index(current_price, base_price)
                route_weight = settings.ROUTE_WEIGHTS.get(route_code, 0.0)
                contribution = round(route_weight * route_index, 6) if route_index is not None else None

                route_indices_for_day[route_code] = route_index

                await upsert_route_index(
                    db,
                    obs_date=calc_date,
                    route_id=route.id,
                    base_price=base_price,
                    current_price=current_price,
                    route_index=route_index,
                    route_weight=route_weight,
                    contribution=contribution,
                )

            # Overall APIx
            apix_value = calculate_airfare_index(route_indices_for_day, settings.ROUTE_WEIGHTS)

            # Daily change
            prev_date = calc_date - timedelta(days=1)
            prev_result = await db.execute(
                __import__("sqlalchemy", fromlist=["select"]).select(
                    __import__("app.db.models", fromlist=["AirfareIndex"]).AirfareIndex
                ).where(
                    __import__("app.db.models", fromlist=["AirfareIndex"]).AirfareIndex.date == prev_date
                )
            )
            prev_ai = prev_result.scalar_one_or_none()
            prev_value = prev_ai.index_value if prev_ai else None
            daily_change = calculate_daily_change(apix_value, prev_value)

            await upsert_airfare_index(
                db,
                obs_date=calc_date,
                index_value=apix_value,
                daily_change_pct=daily_change,
                weekly_change_pct=None,
                monthly_change_pct=None,
                observation_count=len(all_obs),
                coverage_pct=round(valid_obs_count / max(len(all_obs), 1) * 100, 2),
            )

        await db.commit()
        logger.info("index_calculation_completed", days=_num_days)

    return {
        "status": "completed",
        "days_processed": _num_days,
        "observations_generated": len(raw_observations),
    }
