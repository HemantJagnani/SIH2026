import asyncio
import os
import sys
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from models.request import FareSearchRequest
from models.enums import TripType, CabinClass, JobLifecycleStatus
from sources.easemytrip.parser import parse_dom
from storage.models import CollectionRun, RawObservationRecord, FareObservationRecord, Source

async def main():
    db_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:15432/airfare_index")
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    fixture_path = Path("tests/fixtures/easemytrip/del_bom_results.html")
    if not fixture_path.exists():
        print("Fixture not found!")
        return
        
    with open(fixture_path, "r", encoding="utf-8") as f:
        html_content = f.read()
        
    request = FareSearchRequest(
        source="easemytrip",
        collection_mode="BROWSER",
        origin="DEL",
        destination="BOM",
        travel_date=date(2026, 9, 29),
        lead_days=7,
        passenger_count={"adults": 1, "children": 0, "infants": 0},
        cabin=CabinClass.ECONOMY,
        trip_type=TripType.ONE_WAY
    )
    
    run_id = uuid.uuid4()
    job_id = uuid.uuid4()
    
    print("Parsing DOM...")
    observations = parse_dom(html_content, request, run_id, "easemytrip")
    print(f"Parsed {len(observations)} flights.")
    
    async with async_session() as session:
        async with session.begin():
            # Ensure source exists
            from sqlalchemy import select
            src = await session.execute(select(Source).where(Source.name == "easemytrip"))
            if not src.scalar_one_or_none():
                session.add(Source(
                    id=uuid.uuid4(),
                    name="easemytrip",
                    source_type="OTA",
                    permitted_method="WEB",
                    is_active=True
                ))
                await session.flush()
            
            # Create Run
            run = CollectionRun(
                id=run_id,
                created_at=datetime.now(timezone.utc),
                status=JobLifecycleStatus.PUBLISHED.value
            )
            session.add(run)
            await session.flush()
            
            # Create CollectionJob
            from storage.models import CollectionJob
            job = CollectionJob(
                id=uuid.uuid4(),
                run_id=run_id,
                request_id=job_id,
                source_name="easemytrip",
                origin="DEL",
                destination="BOM",
                travel_date=date(2026, 9, 29),
                lead_days=7,
                status=JobLifecycleStatus.PUBLISHED.value
            )
            session.add(job)
            await session.flush()
            
            # Create RawObservationRecord
            raw_obs = RawObservationRecord(
                id=uuid.uuid4(),
                collection_run_id=run_id,
                request_id=job_id,  # dummy job ID for mock
                source_name="easemytrip",
                collection_timestamp=datetime.now(timezone.utc),
                collection_method="BROWSER",
                http_status=200,
                response_time_ms=5000,
                raw_evidence_uri="file://tests/fixtures/easemytrip/del_bom_results.html",
                parser_version="1.0.0",
                adapter_version="1.0.0"
            )
            session.add(raw_obs)
            
            # Create FareObservationRecords
            for obs in observations:
                record = FareObservationRecord(
                    observation_id=obs.observation_id,
                    collection_run_id=obs.collection_run_id,
                    source=obs.source,
                    source_offer_id=obs.source_offer_id,
                    collected_at=obs.collected_at,
                    travel_date=obs.travel_date,
                    lead_days=obs.lead_days,
                    origin=obs.origin,
                    destination=obs.destination,
                    airline=obs.airline,
                    airline_code=obs.airline_code,
                    flight_number=obs.flight_number,
                    trip_type=obs.trip_type.value,
                    cabin=obs.cabin.value,
                    passenger_count=obs.passenger_count,
                    departure_time_local=obs.departure_time_local,
                    departure_time_utc=obs.departure_time_utc,
                    arrival_time_local=obs.arrival_time_local,
                    arrival_time_utc=obs.arrival_time_utc,
                    stops=obs.stops,
                    fare_family=obs.fare_family,
                    fare_class=obs.fare_class,
                    requires_self_transfer=obs.requires_self_transfer,
                    base_fare=obs.base_fare,
                    taxes=obs.taxes,
                    fees=obs.fees,
                    discount=obs.discount,
                    total_fare=obs.total_fare,
                    currency=obs.currency,
                    price_status=obs.price_status,
                    availability=obs.availability.value if hasattr(obs.availability, 'value') else str(obs.availability),
                    adapter_version=obs.adapter_version,
                    normalizer_version=obs.normalizer_version,
                    schema_version=obs.schema_version
                )
                session.add(record)
                
    print("Successfully ingested flights into database!")

if __name__ == "__main__":
    asyncio.run(main())
