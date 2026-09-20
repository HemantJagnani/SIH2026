from datetime import date
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AirfareIndex

async def get_latest_airfare_index(db: AsyncSession) -> Optional[AirfareIndex]:
    """Retrieve the latest airfare index."""
    stmt = select(AirfareIndex).order_by(AirfareIndex.date.desc()).limit(1)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def get_airfare_index_history(
    db: AsyncSession, start_date: Optional[date] = None, end_date: Optional[date] = None
) -> Sequence[AirfareIndex]:
    """Retrieve history of the airfare index within a date range."""
    stmt = select(AirfareIndex).order_by(AirfareIndex.date.asc())
    if start_date:
        stmt = stmt.where(AirfareIndex.date >= start_date)
    if end_date:
        stmt = stmt.where(AirfareIndex.date <= end_date)
    result = await db.execute(stmt)
    return result.scalars().all()
