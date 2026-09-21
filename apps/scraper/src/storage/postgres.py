"""
Async PostgreSQL client using SQLAlchemy and asyncpg.

Provides connection pooling, health checks, and typed data access methods
for the Airfare Index persistence layer.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from storage.models import (
    CollectionJob,
    CollectionRun,
    FareObservationRecord,
    RawObservationRecord,
    Source,
)

logger = logging.getLogger(__name__)


class DatabaseClient:
    """
    Handles all PostgreSQL interactions.
    """

    def __init__(self, database_url: str, pool_size: int = 10, max_overflow: int = 20):
        """
        Initialize the database engine with connection pooling.
        
        Args:
            database_url: e.g., 'postgresql+asyncpg://user:pass@host/db'
            pool_size: Base number of connections to keep open.
            max_overflow: Max number of extra connections to open during spikes.
        """
        self.engine: AsyncEngine = create_async_engine(
            database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            echo=False,
        )
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )

    async def close(self) -> None:
        """Dispose of the engine and close all connections."""
        await self.engine.dispose()
        logger.info("Database engine disposed.")

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Provide a transactional scope around a series of operations."""
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def check_health(self) -> bool:
        """
        Verify database connectivity.
        Returns True if healthy, False otherwise.
        """
        try:
            async with self.engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    # -----------------------------------------------------------------------
    # Typed Helpers
    # -----------------------------------------------------------------------

    async def get_source_by_name(self, source_name: str) -> Source | None:
        async with self.session() as session:
            stmt = select(Source).where(Source.name == source_name)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def insert_collection_run(self, run: CollectionRun) -> CollectionRun:
        async with self.session() as session:
            session.add(run)
            # Returning is automatic as expire_on_commit is False
        return run

    async def insert_raw_observation(self, raw_obs: RawObservationRecord) -> RawObservationRecord:
        async with self.session() as session:
            session.add(raw_obs)
        return raw_obs

    async def insert_fare_observations(self, fare_obs_list: list[FareObservationRecord]) -> None:
        """Bulk insert fare observations."""
        if not fare_obs_list:
            return
        async with self.session() as session:
            session.add_all(fare_obs_list)

    async def get_jobs_for_run(self, run_id: str) -> list[CollectionJob]:
        async with self.session() as session:
            stmt = select(CollectionJob).where(CollectionJob.run_id == run_id)
            result = await session.execute(stmt)
            return list(result.scalars().all())
