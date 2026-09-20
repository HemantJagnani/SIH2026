"""Data quality API endpoint."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.repositories import get_data_quality_stats
from app.schemas import DataQualityResponse

router = APIRouter()


@router.get("", response_model=DataQualityResponse)
async def get_data_quality(db: AsyncSession = Depends(get_db)):
    """
    GET /api/v1/data-quality

    Returns aggregate data quality statistics across all observations.
    """
    stats = await get_data_quality_stats(db)
    return DataQualityResponse(**stats)
