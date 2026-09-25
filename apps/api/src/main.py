import os
import sys
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

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

@app.get("/api/observations")
async def get_observations():
    """
    Fetch all recent fare observations from the local JSON file to populate the dashboard.
    (Modified to skip Docker/PostgreSQL so you can instantly see data on the frontend!)
    """
    json_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'easemytrip_parsed_data.json')
    
    if not os.path.exists(json_path):
        return []

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
            
        # Format the data exactly as the frontend expects it
        formatted_data = []
        for obs in raw_data[:500]:  # Limit to 500 for performance
            formatted_data.append({
                "route": f"{obs.get('origin', '')}→{obs.get('destination', '')}",
                "origin": obs.get("origin"),
                "destination": obs.get("destination"),
                "airline": obs.get("airline"),
                "airline_code": obs.get("airline_code"),
                "flight_number": obs.get("flight_number"),
                "cabin": obs.get("cabin", "ECONOMY"),
                "travel_date": obs.get("travel_date"),
                "lead_days": obs.get("lead_days"),
                "total_fare": float(obs.get("total_fare", 0) or 0),
                "base_fare": float(obs.get("base_fare", 0) or 0),
                "taxes": float(obs.get("taxes", 0) or 0),
                "source": obs.get("source"),
                "availability": obs.get("availability", "AVAILABLE"),
                "collected_at": obs.get("collected_at"),
                "fare_family": obs.get("fare_family"),
                "stops": obs.get("stops", 0),
                "price_status": obs.get("price_status", "OK"),
                "requires_self_transfer": obs.get("requires_self_transfer", False),
                "departure_time_local": obs.get("departure_time_local"),
                "arrival_time_local": obs.get("arrival_time_local"),
                "collection_mode": "JSON Backup"
            })
        return formatted_data
    except Exception as e:
        print(f"Error reading JSON: {e}")
        return []
