import os
import sys
import uuid
from datetime import date
from typing import Any
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

from adapters.base import FareSourceAdapter
from adapters.models import CollectionMode, CollectionStatus, FareSearchRequest
from models.observation import CabinClass, TripType


class DummyAdapter(FareSourceAdapter):
    
    @property
    def adapter_version(self) -> str:
        return "1.0.0"

    @property
    def parser_version(self) -> str:
        return "1.0.0"

    async def _fetch(self, request: FareSearchRequest) -> tuple[Any, int | None]:
        if request.origin == "ERR":
            raise ValueError("Test error during fetch")
        if request.origin == "EMP":
            return None, 200
        return {"data": "test_data"}, 200

    def _parse(self, raw_data: Any, request: FareSearchRequest) -> list:
        if request.destination == "NOP":
            return []
        
        # Return a valid dummy FareObservation object so Pydantic validation passes
        from models.observation import AvailabilityStatus, CabinClass, FareObservation, TripType
        from datetime import datetime, timezone
        
        dummy_obs = FareObservation(
            collection_run_id=uuid.uuid4(),
            source="dummy",
            collected_at=datetime.now(timezone.utc),
            travel_date=date(2026, 9, 21),
            lead_days=1,
            origin="DEL",
            destination="BOM",
            airline="Dummy Air",
            trip_type=TripType.ONE_WAY,
            cabin=CabinClass.ECONOMY,
            passenger_count=1,
            currency="INR",
            availability=AvailabilityStatus.AVAILABLE,
            adapter_version="1.0.0",
            normalizer_version="1.0.0",
            schema_version="1.0.0"
        )
        return [dummy_obs]


@pytest.fixture
def base_request() -> FareSearchRequest:
    return FareSearchRequest(
        source="dummy",
        origin="DEL",
        destination="BOM",
        travel_date=date(2026, 9, 21),
        lead_days=1,
        collection_mode=CollectionMode.API
    )


@pytest.mark.asyncio
async def test_adapter_success(base_request):
    adapter = DummyAdapter()
    result = await adapter.collect(base_request)
    
    assert result.status == CollectionStatus.SUCCESS
    assert len(result.observations) == 1
    assert result.observations[0].source == "dummy"
    assert result.http_status == 200
    assert result.adapter_version == "1.0.0"
    assert result.parser_version == "1.0.0"


@pytest.mark.asyncio
async def test_adapter_no_results_from_fetch():
    request = FareSearchRequest(
        source="dummy",
        origin="EMP",
        destination="BOM",
        travel_date=date(2026, 9, 21),
        lead_days=1,
        collection_mode=CollectionMode.API
    )
    adapter = DummyAdapter()
    result = await adapter.collect(request)
    
    assert result.status == CollectionStatus.NO_RESULTS
    assert result.observations == []


@pytest.mark.asyncio
async def test_adapter_no_results_from_parser():
    request = FareSearchRequest(
        source="dummy",
        origin="DEL",
        destination="NOP",
        travel_date=date(2026, 9, 21),
        lead_days=1,
        collection_mode=CollectionMode.API
    )
    adapter = DummyAdapter()
    result = await adapter.collect(request)
    
    assert result.status == CollectionStatus.NO_RESULTS
    assert result.observations == []


@pytest.mark.asyncio
async def test_adapter_fetch_exception():
    request = FareSearchRequest(
        source="dummy",
        origin="ERR",
        destination="BOM",
        travel_date=date(2026, 9, 21),
        lead_days=1,
        collection_mode=CollectionMode.API
    )
    adapter = DummyAdapter()
    result = await adapter.collect(request)
    
    assert result.status == CollectionStatus.SOURCE_ERROR
    assert result.error_message == "Test error during fetch"
    assert result.observations == []
