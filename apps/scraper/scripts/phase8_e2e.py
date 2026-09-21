import asyncio
import os
import sys
import uuid
import logging
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from adapters.models import FareSearchRequest, CollectionMode
from models.observation import TripType, CabinClass
from sources.cleartrip.adapter import CleartripFlightApiAdapter
from storage.postgres import DatabaseClient
from storage.object_store import S3ObjectStoreClient
from storage.models import Base, FareObservationRecord, CollectionRun, Source
from validation.pipeline import validate_observation

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

async def main():
    # 1. Setup Request (DEL -> BOM, T+7, 1 Adult, Economy, One-Way)
    request = FareSearchRequest(
        source="cleartrip",
        origin="DEL",
        destination="BOM",
        travel_date=date(2026, 9, 28),
        lead_days=7,
        trip_type=TripType.ONE_WAY,
        cabin=CabinClass.ECONOMY,
        adults=1,
        currency="INR",
        collection_mode=CollectionMode.API
    )
    logger.info(f"Created request: {request.origin}->{request.destination} on {request.travel_date}")

    # 2. Run through Adapter (Mocked)
    adapter = CleartripFlightApiAdapter(use_mock=True)
    result = await adapter.collect(request)
    logger.info(f"Collection status: {result.status}, found {len(result.observations)} observations.")

    if not result.observations:
        logger.warning("No observations found, exiting.")
        return

    # 3. Setup Storage
    pg_client = DatabaseClient(database_url=os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:15432/airfare_index"))
    os_client = S3ObjectStoreClient(
        endpoint_url=os.getenv("S3_ENDPOINT", "http://localhost:9000"),
        aws_access_key_id=os.getenv("S3_ACCESS_KEY", "minioadmin"),
        aws_secret_access_key=os.getenv("S3_SECRET_KEY", "minioadmin"),
        bucket_name="raw-evidence"
    )
    
    # Initialize DB (creates tables if missing for the test)
    # The engine is created automatically in DatabaseClient.__init__
    
    # 4. Save Raw Evidence
    collection_run_id = uuid.uuid4()
    # Assuming the raw evidence is the JSON string representation of the parsed result for this mock
    # In a real run, adapter._fetch would return the raw payload and we'd access it. 
    # For now, we mock the evidence save.
    try:
        raw_uri = await os_client.upload_raw_evidence(
            source="cleartrip", 
            collection_date=request.travel_date,
            collection_run_id=str(collection_run_id), 
            filename="response.json",
            content=b'{"mock": "evidence"}', 
            content_type="application/json"
        )
        logger.info(f"Saved raw evidence to {raw_uri}")
    except Exception as e:
        logger.warning(f"Failed to save to object store (MinIO might not be running): {e}")

    # 5. Insert Run First
    run = CollectionRun(id=collection_run_id, status="COMPLETED")
    await pg_client.insert_collection_run(run)

    # 6. Normalize and Validate
    for obs in result.observations:
        obs.collection_run_id = collection_run_id
        
        # We need to convert FareObservation to dict for our pipelines
        obs_dict = obs.model_dump()
        
        # Apply Validation
        valid_obs, val_result = validate_observation(obs_dict)
        if not val_result.is_valid:
            logger.error(f"Validation failed for {obs.flight_number}: {val_result.errors}")
            continue
            
        logger.info(f"Validation successful for {obs.flight_number}")
        
        # 6. Store Canonical Result
        norm_data = valid_obs.model_dump()
        
        # We ensure the source exists
        source_name = norm_data["source"]
        existing_source = await pg_client.get_source_by_name(source_name)
        if not existing_source:
            async with pg_client.session() as session:
                new_source = Source(name=source_name, source_type="OTA", permitted_method="API")
                session.add(new_source)
                await session.commit()
        
        # Map to SQLAlchemy record
        record = FareObservationRecord(
            observation_id=norm_data["observation_id"],
            collection_run_id=norm_data["collection_run_id"],
            source=norm_data["source"],
            source_offer_id=norm_data.get("source_offer_id"),
            collected_at=norm_data["collected_at"],
            travel_date=norm_data["travel_date"],
            lead_days=norm_data["lead_days"],
            origin=norm_data["origin"],
            destination=norm_data["destination"],
            airline=norm_data["airline"],
            airline_code=norm_data.get("airline_code"),
            flight_number=norm_data.get("flight_number"),
            trip_type=norm_data["trip_type"],
            cabin=norm_data["cabin"],
            passenger_count=norm_data["passenger_count"],
            departure_time=norm_data.get("departure_time"),
            arrival_time=norm_data.get("arrival_time"),
            stops=norm_data.get("stops"),
            fare_family=norm_data.get("fare_family"),
            fare_class=norm_data.get("fare_class"),
            base_fare=norm_data.get("base_fare"),
            taxes=norm_data.get("taxes"),
            fees=norm_data.get("fees"),
            discount=norm_data.get("discount"),
            total_fare=norm_data.get("total_fare"),
            currency=norm_data["currency"],
            availability=norm_data["availability"],
            raw_value_reference=norm_data.get("raw_value_reference"),
            raw_evidence_uri=norm_data.get("raw_evidence_uri"),
            adapter_version=norm_data["adapter_version"],
            normalizer_version=norm_data["normalizer_version"],
            schema_version=norm_data["schema_version"]
        )
        
        await pg_client.insert_fare_observations([record])
        logger.info(f"Saved canonical observation {obs.flight_number} to PostgreSQL")

    logger.info("End-to-End Pipeline test completed successfully.")
    await pg_client.close()


if __name__ == "__main__":
    asyncio.run(main())
