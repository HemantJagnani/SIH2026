from datetime import date
from typing import Sequence, Tuple, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models import Route, RouteIndex, RouteDailyPrice

async def get_all_routes(db: AsyncSession) -> Sequence[Route]:
    stmt = select(Route).where(Route.active == True)
    result = await db.execute(stmt)
    return result.scalars().all()

async def get_route_by_code(db: AsyncSession, route_code: str) -> Optional[Route]:
    stmt = select(Route).where(Route.route_code == route_code, Route.active == True)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def get_route_indices_for_date(db: AsyncSession, query_date: date) -> Sequence[Tuple[RouteIndex, Route]]:
    stmt = select(RouteIndex, Route).join(Route).where(RouteIndex.date == query_date)
    result = await db.execute(stmt)
    return result.all()

async def get_route_daily_prices_for_date(db: AsyncSession, query_date: date, route_id: int) -> Sequence[RouteDailyPrice]:
    stmt = select(RouteDailyPrice).where(
        RouteDailyPrice.date == query_date,
        RouteDailyPrice.route_id == route_id
    )
    result = await db.execute(stmt)
    return result.scalars().all()

async def get_route_index_history(db: AsyncSession, route_id: int) -> Sequence[RouteIndex]:
    stmt = select(RouteIndex).where(RouteIndex.route_id == route_id).order_by(RouteIndex.date.asc())
    result = await db.execute(stmt)
    return result.scalars().all()
