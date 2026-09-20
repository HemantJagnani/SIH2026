"""Index API endpoints."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.repositories import get_latest_airfare_index, get_airfare_index_history
from app.schemas import CurrentIndexResponse, IndexHistoryResponse, IndexHistoryPoint

router = APIRouter()

DISCLAIMER = (
    "Illustrative POC methodology — subject to validation against "
    "MoSPI, DGCA and international price-index standards."
)


@router.get("/current", response_model=CurrentIndexResponse)
async def get_current_index(db: AsyncSession = Depends(get_db)):
    """
    GET /api/v1/index/current

    Returns the most recent Airfare Price Index value.
    """
    latest = await get_latest_airfare_index(db)
    if latest is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "NO_INDEX_DATA",
                    "message": "No index data found. Run ingestion first via POST /api/v1/ingestion/run",
                }
            },
        )
    return CurrentIndexResponse(
        date=latest.date,
        index_value=round(latest.index_value, 2),
        daily_change_pct=round(latest.daily_change_pct, 4) if latest.daily_change_pct else None,
        weekly_change_pct=round(latest.weekly_change_pct, 4) if latest.weekly_change_pct else None,
        monthly_change_pct=round(latest.monthly_change_pct, 4) if latest.monthly_change_pct else None,
        observation_count=latest.observation_count,
        coverage_pct=latest.coverage_pct,
        disclaimer=DISCLAIMER,
    )


@router.get("/history", response_model=IndexHistoryResponse)
async def get_index_history(
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    GET /api/v1/index/history?start_date=2026-09-01&end_date=2026-09-20

    Returns daily APIx values over a date range.
    """
    records = await get_airfare_index_history(db, start_date=start_date, end_date=end_date)
    data = [
        IndexHistoryPoint(
            date=r.date,
            index_value=round(r.index_value, 4) if r.index_value else None,
            daily_change_pct=round(r.daily_change_pct, 4) if r.daily_change_pct else None,
        )
        for r in records
    ]
    effective_start = start_date or (data[0].date if data else date.today())
    effective_end = end_date or (data[-1].date if data else date.today())
    return IndexHistoryResponse(
        data=data,
        count=len(data),
        start_date=effective_start,
        end_date=effective_end,
    )
