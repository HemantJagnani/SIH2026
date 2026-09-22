import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Ensure we can import from apps.scraper.src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'scraper', 'src')))

from storage.models import FareObservationRecord, RawObservationRecord

load_dotenv()

app = FastAPI(title="India Airfare Index API")

# Add CORS so the dashboard can fetch from this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup Database Connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:15432/airfare_index")
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

@app.get("/api/observations")
async def get_observations():
    """
    Fetch all recent fare observations from the database to populate the dashboard.
    """
    async with async_session() as session:
        # Fetch the latest 500 observations sorted by travel date with collection method
        stmt = (
            select(FareObservationRecord, RawObservationRecord.collection_method)
            .outerjoin(RawObservationRecord, FareObservationRecord.collection_run_id == RawObservationRecord.collection_run_id)
            .order_by(FareObservationRecord.travel_date)
            .limit(500)
        )
        result = await session.execute(stmt)
        rows = result.all()
        
        # Convert SQLAlchemy models to dicts
        return [
            {
                "route": f"{obs.origin}→{obs.destination}",
                "origin": obs.origin,
                "destination": obs.destination,
                "airline": obs.airline,
                "airline_code": obs.airline_code,
                "flight_number": obs.flight_number,
                "cabin": obs.cabin if obs.cabin else "ECONOMY",
                "travel_date": obs.travel_date.isoformat() if obs.travel_date else None,
                "lead_days": obs.lead_days,
                "total_fare": float(obs.total_fare) if obs.total_fare else 0,
                "base_fare": float(obs.base_fare) if obs.base_fare else 0,
                "taxes": float(obs.taxes) if obs.taxes else 0,
                "source": obs.source,
                "availability": obs.availability if obs.availability else "AVAILABLE",
                "collected_at": obs.collected_at.isoformat() if obs.collected_at else None,
                "fare_family": obs.fare_family,
                "stops": obs.stops,
                "price_status": obs.price_status,
                "requires_self_transfer": obs.requires_self_transfer,
                "departure_time_local": obs.departure_time_local.isoformat() if obs.departure_time_local else None,
                "arrival_time_local": obs.arrival_time_local.isoformat() if obs.arrival_time_local else None,
                "collection_mode": col_method if col_method else "API"
            }
            for obs, col_method in rows
        ]
