"""
Tests for EntityMapper (database-backed normalization).
"""
import os
import sys

import pytest
import pytest_asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

from normalization import EntityMapper, NormalizationException
from storage.postgres import DatabaseClient

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL", 
    "postgresql+asyncpg://postgres:postgres@localhost:15432/airfare_index"
)


@pytest_asyncio.fixture(scope="module")
async def db_client():
    client = DatabaseClient(TEST_DB_URL)
    yield client
    await client.close()


@pytest_asyncio.fixture(scope="module")
async def loaded_mapper(db_client):
    mapper = EntityMapper()
    await mapper.load(db_client)
    return mapper


@pytest.mark.asyncio
async def test_normalize_airport(loaded_mapper):
    """Test global airport mappings that were loaded from YAML."""
    res = loaded_mapper.normalize_airport("indigo", "delhi")
    assert res.normalized_value == "DEL"
    
    res2 = loaded_mapper.normalize_airport("makemytrip", "chhatrapati shivaji maharaj")
    assert res2.normalized_value == "BOM"
    
    res3 = loaded_mapper.normalize_airport("cleartrip", "KEMPEGOWDA")
    assert res3.normalized_value == "BLR"


@pytest.mark.asyncio
async def test_normalize_airline(loaded_mapper):
    """Test global airline mappings that were loaded from YAML."""
    res = loaded_mapper.normalize_airline("cleartrip", "6E")
    assert res.normalized_value == "IndiGo"
    
    res2 = loaded_mapper.normalize_airline("makemytrip", "Air India Express")
    assert res2.normalized_value == "Air India Express"
    
    res3 = loaded_mapper.normalize_airline("yatra", "qp")
    assert res3.normalized_value == "Akasa Air"


@pytest.mark.asyncio
async def test_normalize_entity_exception(loaded_mapper):
    """Test that unknown entities deterministically raise exceptions."""
    with pytest.raises(NormalizationException) as exc:
        loaded_mapper.normalize_airport("indigo", "UNKNOWN_AIRPORT")
    
    assert "No deterministic mapping found" in str(exc.value)
