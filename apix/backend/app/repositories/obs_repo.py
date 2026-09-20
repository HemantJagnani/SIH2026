from datetime import date
from typing import Sequence, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models import FareObservation

async def get_observations(
    db: AsyncSession,
    route_code: Optional[str] = None,
    travel_date: Optional[date] = None,
    limit: int = 100,
    offset: int = 0
) -> Sequence[FareObservation]:
    stmt = select(FareObservation).options(
        joinedload(FareObservation.route),
        joinedload(FareObservation.airline),
        joinedload(FareObservation.source)
    ).order_by(FareObservation.search_timestamp.desc())
    
    if route_code:
        # Assuming we can join or filter... simpler way since we joinedload Route:
        from app.db.models import Route
        stmt = stmt.join(Route).where(Route.route_code == route_code)
    if travel_date:
        stmt = stmt.where(FareObservation.travel_date == travel_date)
        
    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    return result.scalars().all()
