"""
Integration tests for PostgreSQL DatabaseClient.

Requires a running test PostgreSQL database (configured via TEST_DATABASE_URL).
"""

import os
import sys
import uuid
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

from storage.models import CollectionRun, Source
from storage.postgres import DatabaseClient

# Default to the local docker instance if not explicitly set
TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL", 
    "postgresql+asyncpg://postgres:postgres@localhost:15432/airfare_index"
)


import pytest_asyncio

@pytest_asyncio.fixture
async def db_client():
    """Provides a connected DatabaseClient for testing."""
    client = DatabaseClient(TEST_DB_URL, pool_size=2, max_overflow=2)
    yield client
    await client.close()


@pytest.mark.asyncio
async def test_database_health_check(db_client):
    """Test that the DB is reachable."""
    is_healthy = await db_client.check_health()
    assert is_healthy is True


@pytest.mark.asyncio
async def test_insert_and_get_source(db_client):
    """Test inserting and retrieving a source."""
    source_name = f"test_source_{uuid.uuid4().hex[:8]}"
    new_source = Source(
        name=source_name,
        source_type="TEST",
        permitted_method="API",
    )
    
    async with db_client.session() as session:
        session.add(new_source)
        
    retrieved = await db_client.get_source_by_name(source_name)
    assert retrieved is not None
    assert retrieved.name == source_name
    assert retrieved.source_type == "TEST"
    assert retrieved.is_active is True


@pytest.mark.asyncio
async def test_insert_collection_run(db_client):
    """Test inserting a collection run."""
    run_id = uuid.uuid4()
    run = CollectionRun(
        id=run_id,
        status="IN_PROGRESS",
    )
    inserted_run = await db_client.insert_collection_run(run)
    assert inserted_run.id == run_id
    assert inserted_run.status == "IN_PROGRESS"
    assert inserted_run.created_at is not None
