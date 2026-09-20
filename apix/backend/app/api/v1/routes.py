"""Routes API endpoints."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.repositories import (
    get_all_routes,
    get_route_by_code,
    get_latest_airfare_index,
    get_route_indices_for_date,
    get_route_daily_prices_for_date,
    get_route_index_history,
)
from app.schemas import (
    RoutesListResponse,
    RouteResponse,
    RouteDetailResponse,
    LeadTimePrice,
    RouteHistoryPoint,
)

router = APIRouter()

DISCLAIMER = "Illustrative POC route weights — not official weights."


@router.get("", response_model=RoutesListResponse)
async def list_routes(db: AsyncSession = Depends(get_db)):
    """
    GET /api/v1/routes

    Returns all routes with their current index values and weights.
    """
    latest = await get_latest_airfare_index(db)
    latest_date = latest.date if latest else None

    routes = await get_all_routes(db)
    if not routes:
        return RoutesListResponse(data=[], count=0, disclaimer=DISCLAIMER)

    # Get route indices for the latest date
    if latest_date:
        route_indices = await get_route_indices_for_date(db, latest_date)
        ri_map = {ri.route_id: ri for ri, _ in route_indices}
    else:
        ri_map = {}

    result = []
    for route in routes:
        ri = ri_map.get(route.id)
        # Get lead-time prices for latest date
        lead_time_prices = []
        if latest_date:
            rdps = await get_route_daily_prices_for_date(db, latest_date, route.id)
            lead_time_prices = [
                LeadTimePrice(
                    lead_days=rdp.lead_days,
                    representative_price=rdp.representative_price,
                    observation_count=rdp.observation_count,
                    valid_observation_count=rdp.valid_observation_count,
                )
                for rdp in sorted(rdps, key=lambda x: x.lead_days)
            ]

        result.append(
            RouteResponse(
                route_code=route.route_code,
                origin=route.origin,
                destination=route.destination,
                weight=route.weight,
                base_price=ri.base_price if ri else 0.0,
                current_price=ri.current_price if ri else None,
                route_index=round(ri.route_index, 4) if ri and ri.route_index else None,
                contribution=round(ri.contribution, 4) if ri and ri.contribution else None,
                lead_time_prices=lead_time_prices,
                date=latest_date,
                disclaimer=DISCLAIMER,
            )
        )

    return RoutesListResponse(data=result, count=len(result), disclaimer=DISCLAIMER)


@router.get("/{route_code}", response_model=RouteDetailResponse)
async def get_route_detail(
    route_code: str,
    db: AsyncSession = Depends(get_db),
):
    """
    GET /api/v1/routes/DEL-BOM

    Returns detailed information for a specific route including history.
    """
    route = await get_route_by_code(db, route_code.upper())
    if route is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "ROUTE_NOT_FOUND",
                    "message": f"Route {route_code.upper()} does not exist.",
                }
            },
        )

    latest = await get_latest_airfare_index(db)
    latest_date = latest.date if latest else None

    # Latest route index
    latest_ri = None
    lead_time_prices = []
    if latest_date:
        route_indices = await get_route_indices_for_date(db, latest_date)
        ri_map = {ri.route_id: ri for ri, _ in route_indices}
        latest_ri = ri_map.get(route.id)
        rdps = await get_route_daily_prices_for_date(db, latest_date, route.id)
        lead_time_prices = [
            LeadTimePrice(
                lead_days=rdp.lead_days,
                representative_price=rdp.representative_price,
                observation_count=rdp.observation_count,
                valid_observation_count=rdp.valid_observation_count,
            )
            for rdp in sorted(rdps, key=lambda x: x.lead_days)
        ]

    # Historical route index
    history_records = await get_route_index_history(db, route.id)
    history = [
        RouteHistoryPoint(
            date=ri.date,
            route_index=round(ri.route_index, 4) if ri.route_index else None,
            current_price=ri.current_price,
        )
        for ri in history_records
    ]

    return RouteDetailResponse(
        route_code=route.route_code,
        origin=route.origin,
        destination=route.destination,
        weight=route.weight,
        base_price=latest_ri.base_price if latest_ri else 0.0,
        current_price=latest_ri.current_price if latest_ri else None,
        route_index=round(latest_ri.route_index, 4) if latest_ri and latest_ri.route_index else None,
        contribution=round(latest_ri.contribution, 4) if latest_ri and latest_ri.contribution else None,
        lead_time_prices=lead_time_prices,
        history=history,
        date=latest_date,
        disclaimer=DISCLAIMER,
    )
