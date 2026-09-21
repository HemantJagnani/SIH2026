import sys
import os
import asyncio
import uuid
import json
from datetime import date, timedelta
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'scraper', 'src')))

from adapters.ignav import IgnavAdapter
from adapters.models import FareSearchRequest
from models.enums import TripType, CabinClass
from storage.postgres import DatabaseClient
from storage.models import FareObservationRecord, CollectionRun, CollectionJob
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run():
    logger.info("Initializing Ignav Adapter...")
    adapter = IgnavAdapter()
    
    if not adapter.api_key:
        logger.error("IGNAV_API_KEY missing in .env! Please add it before running.")
        return
    
    # 1 request: DEL -> BOM, 7 days out
    travel_date = date.today() + timedelta(days=7)
    
    request = FareSearchRequest(
        request_id=uuid.uuid4(),
        source="ignav",
        origin="DEL",
        destination="BOM",
        travel_date=travel_date,
        lead_days=7,
        trip_type=TripType.ONE_WAY,
        cabin=CabinClass.ECONOMY,
        adults=1,
        children=0,
        infants=0,
        currency="INR",
        collection_mode="API"
    )

    logger.info(f"Loading live data fixture for {request.origin} -> {request.destination} on {request.travel_date}...")
    
    fixture_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tests', 'adapters', 'ignav_raw_fixture.json'))
    with open(fixture_path, 'r') as f:
        raw_response = json.load(f)
        
    logger.info("Parsing raw response into FareObservations...")
    observations = adapter._parse(raw_response, request)
    logger.info(f"Successfully parsed {len(observations)} observations.")
    
    if observations:
        logger.info("Initializing Database...")
        db = DatabaseClient(database_url=os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:15432/airfare_index"))
        # Drop and recreate tables to ensure schema matches the new models
        async with db.engine.begin() as conn:
            await conn.execute(text("DROP TABLE IF EXISTS fare_observations CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS raw_observations CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS collection_jobs CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS collection_runs CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS sources CASCADE"))
            from storage.models import Base
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Saving observations to PostgreSQL...")
        
            
        records = [
            FareObservationRecord(
                observation_id=obs.observation_id,
                collection_run_id=obs.collection_run_id,
                source=obs.source,
                source_itinerary_id=obs.source_itinerary_id,
                collected_at=obs.collected_at,
                travel_date=obs.travel_date,
                lead_days=obs.lead_days,
                origin=obs.origin,
                destination=obs.destination,
                airline=obs.airline,
                airline_code=obs.airline_code,
                flight_number=obs.flight_number,
                trip_type=obs.trip_type.name,
                cabin=obs.cabin.name,
                passenger_count=obs.passenger_count,
                departure_time_local=obs.departure_time_local,
                departure_time_utc=obs.departure_time_utc,
                arrival_time_local=obs.arrival_time_local,
                arrival_time_utc=obs.arrival_time_utc,
                stops=obs.stops,
                fare_family=obs.fare_family,
                fare_class=obs.fare_class,
                requires_self_transfer=obs.requires_self_transfer,
                total_fare=obs.total_fare,
                currency=obs.currency,
                price_status=obs.price_status,
                availability=obs.availability.name,
                adapter_version=obs.adapter_version,
                normalizer_version=obs.normalizer_version,
                schema_version=obs.schema_version
            ) for obs in observations
        ]
        
        # Need to create dummy run and job for the foreign keys to work
        run = CollectionRun(id=request.request_id, status="COMPLETED")
        job = CollectionJob(
            id=request.request_id,
            run_id=run.id,
            request_id=request.request_id,
            source_name="ignav",
            origin=request.origin,
            destination=request.destination,
            travel_date=request.travel_date,
            lead_days=request.lead_days,
            status="COMPLETED"
        )
        
        from storage.models import Source
        ignav_source = Source(name="ignav", source_type="OTA", permitted_method="API")
        
        async with db.session() as session:
            session.add(ignav_source)
            session.add(run)
            await session.flush()
            session.add(job)
            await session.flush()
            session.add_all(records)
            
        logger.info("Done! Observations saved successfully.")
    else:
        logger.warning("No observations were returned.")

if __name__ == "__main__":
    asyncio.run(run())
