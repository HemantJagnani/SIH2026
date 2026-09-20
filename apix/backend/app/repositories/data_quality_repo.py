from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from app.db.models import FareObservation

async def get_data_quality_stats(db: AsyncSession) -> Dict[str, Any]:
    # Total observations
    total = await db.scalar(select(func.count()).select_from(FareObservation))

    # Valid
    valid = await db.scalar(select(func.count()).where(FareObservation.quality_status == "valid"))

    # Invalid
    invalid = await db.scalar(select(func.count()).where(FareObservation.quality_status == "invalid"))

    # Missing
    missing = await db.scalar(select(func.count()).where(FareObservation.quality_status == "missing"))

    # Sold out
    sold_out = await db.scalar(select(func.count()).where(FareObservation.availability == "sold_out"))

    # Duplicates
    duplicates = await db.scalar(select(func.count()).where(FareObservation.quality_status == "duplicate"))

    # Outliers
    outliers = await db.scalar(select(func.count()).where(FareObservation.outlier_flag == True))

    coverage_pct = round((valid / total * 100), 2) if total and total > 0 else 0.0

    return {
        "total_observations": total or 0,
        "valid": valid or 0,
        "invalid": invalid or 0,
        "missing": missing or 0,
        "sold_out": sold_out or 0,
        "duplicates": duplicates or 0,
        "outliers": outliers or 0,
        "coverage_pct": coverage_pct,
    }

