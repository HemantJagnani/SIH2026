import os
import uuid
from datetime import date
from pathlib import Path
import json

from models.request import FareSearchRequest
from models.enums import TripType, CabinClass
from sources.easemytrip.parser import parse_dom

def main():
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
    
    print("Parsing DOM...")
    observations = parse_dom(html_content, request, run_id, "easemytrip")
    print(f"Extracted {len(observations)} flights.")
    
    # Dump to JSON for inspection
    out_file = Path("easemytrip_parsed_data.json")
    
    obs_list = []
    for obs in observations:
        # Convert to dict, serialize UUIDs/datetimes for JSON
        obs_dict = obs.model_dump(mode="json")
        obs_list.append(obs_dict)
        
    with open(out_file, "w") as f:
        json.dump(obs_list, f, indent=2)
        
    print(f"\nSaved all {len(observations)} records to {out_file.absolute()}")
    
    # Print top 10 nicely
    print("\n--- TOP 10 FLIGHTS ---")
    print(f"{'Airline':<15} | {'Flight No':<10} | {'Fare':<8} | {'Stops':<5}")
    print("-" * 50)
    for obs in observations[:10]:
        stops_str = str(obs.stops) if obs.stops is not None else "Unknown"
        print(f"{obs.airline:<15} | {obs.flight_number:<10} | Rs.{obs.total_fare:<7.2f} | {stops_str:<5}")
        
if __name__ == "__main__":
    main()
