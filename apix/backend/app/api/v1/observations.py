"""Observations API endpoint."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.repositories import get_observations
from app.schemas import ObservationsResponse, ObservationSchema

router = APIRouter()


@router.get("", response_model=ObservationsResponse)
async def list_observations(
    route: Optional[str] = Query(default=None, description="Route code e.g. DEL-BOM"),
    airline: Optional[str] = Query(default=None, description="Airline code e.g. 6E"),
    quality_status: Optional[str] = Query(default=None, description="valid | invalid | missing | duplicate"),
    lead_days: Optional[int] = Query(default=None, description="Lead days: 1, 7, or 30"),
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """
    GET /api/v1/observations

    Returns paginated fare observations with optional filters.
    Every index value is traceable back to source observations.
    """
    records, total = await get_observations(
        db,
        route_code=route,
        airline_code=airline,
        quality_status=quality_status,
        lead_days=lead_days,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )

    obs_schemas = [ObservationSchema(**r) for r in records]

    return ObservationsResponse(
        data=obs_schemas,
        count=len(obs_schemas),
        total=total,
        page=page,
        page_size=page_size,
    )
