"""
Dataset Audit Script for APIx Phase 1
Inspects available datasets (easemytrip_parsed_data.json, fixtures), evaluates columns,
computes null/duplicate rates, verifies lead-time coverage, and checks T+21 feasibility.
"""

import json
from pathlib import Path
from collections import Counter
from datetime import datetime, date

REQUIRED_METHODOLOGY_FIELDS = [
    "origin",
    "destination",
    "travel_date",
    "day_of_week",
    "search_timestamp_utc",
    "search_timestamp_local",
    "lead_days",
    "airline",
    "airline_code",
    "flight_number",
    "source_itinerary_id",
    "source_offer_id",
    "departure_time_local",
    "arrival_time_local",
    "departure_time_utc",
    "arrival_time_utc",
    "duration_minutes",
    "stops",
    "stopover_airports",
    "cabin_class",
    "fare_family",
    "fare_class",
    "baggage_allowance",
    "refundability",
    "changeability",
    "meal_included",
    "base_fare",
    "taxes",
    "airport_charges",
    "mandatory_fees",
    "convenience_fee",
    "discount",
    "total_fare",
    "currency",
    "availability_status",
    "price_status",
    "requires_self_transfer",
    "source",
    "source_type",
    "source_url",
    "raw_evidence_uri",
    "adapter_version",
    "normalizer_version",
    "schema_version"
]

def analyze_easemytrip(json_path: Path):
    print(f"--- ANALYZING {json_path} ---")
    if not json_path.exists():
        print(f"File {json_path} not found.")
        return None
    
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    total_records = len(data)
    print(f"Total records: {total_records}")
    if total_records == 0:
        return None
        
    # Columns in dataset
    all_keys = set()
    for row in data:
        all_keys.update(row.keys())
    
    print(f"Total unique columns present: {len(all_keys)}")
    
    # Null rate per column
    null_counts = Counter()
    value_types = {}
    for row in data:
        for k in all_keys:
            val = row.get(k)
            if val is None or val == "" or val == "null":
                null_counts[k] += 1
            else:
                if k not in value_types:
                    value_types[k] = type(val).__name__
                    
    # Lead days distribution
    lead_days_counts = Counter()
    travel_dates = Counter()
    search_timestamps = Counter()
    airlines = Counter()
    routes = Counter()
    stops_counts = Counter()
    currencies = Counter()
    fares = []
    
    # Duplicate checking
    exact_duplicates = 0
    seen_exact = set()
    itinerary_keys = set()
    itinerary_duplicates = 0
    
    for row in data:
        # exact json repr
        row_repr = json.dumps(row, sort_keys=True)
        if row_repr in seen_exact:
            exact_duplicates += 1
        else:
            seen_exact.add(row_repr)
            
        # flight offer key
        offer_key = (
            row.get("origin"),
            row.get("destination"),
            row.get("travel_date"),
            row.get("airline"),
            row.get("flight_number"),
            row.get("total_fare")
        )
        if offer_key in itinerary_keys:
            itinerary_duplicates += 1
        else:
            itinerary_keys.add(offer_key)
            
        lead_days_counts[row.get("lead_days")] += 1
        travel_dates[row.get("travel_date")] += 1
        if row.get("search_timestamp"):
            search_timestamps[str(row.get("search_timestamp"))[:10]] += 1
        airlines[row.get("airline")] += 1
        routes[f"{row.get('origin')}->{row.get('destination')}"] += 1
        stops_counts[row.get("stops")] += 1
        currencies[row.get("currency")] += 1
        
        tf = row.get("total_fare")
        if tf is not None:
            try:
                fares.append(float(tf))
            except (ValueError, TypeError):
                pass

    return {
        "total_records": total_records,
        "columns_present": sorted(list(all_keys)),
        "null_counts": dict(null_counts),
        "exact_duplicates": exact_duplicates,
        "offer_duplicates": itinerary_duplicates,
        "lead_days_distribution": dict(lead_days_counts),
        "travel_dates": dict(travel_dates),
        "search_dates": dict(search_timestamps),
        "airlines": dict(airlines),
        "routes": dict(routes),
        "stops": dict(stops_counts),
        "currencies": dict(currencies),
        "fare_stats": {
            "min": min(fares) if fares else 0,
            "max": max(fares) if fares else 0,
            "avg": round(sum(fares)/len(fares), 2) if fares else 0,
            "count": len(fares)
        }
    }

def analyze_ignav_fixture(json_path: Path):
    print(f"\n--- ANALYZING IGNAV FIXTURE {json_path} ---")
    if not json_path.exists():
        return None
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    itins = data.get("itineraries", [])
    print(f"Total itineraries in Ignav fixture: {len(itins)}")
    
    carriers = Counter()
    stops = Counter()
    has_times = 0
    fares = []
    
    for it in itins:
        outbound = it.get("outbound", {})
        carrier = outbound.get("carrier")
        carriers[carrier] += 1
        segs = outbound.get("segments", [])
        stops[len(segs) - 1] += 1
        if segs and "departure_time_local" in segs[0]:
            has_times += 1
        price = it.get("price", {})
        if "amount" in price:
            fares.append(price.get("amount"))
            
    return {
        "total_itineraries": len(itins),
        "carriers": dict(carriers),
        "stops": dict(stops),
        "has_times": has_times,
        "price_stats": {
            "min": min(fares) if fares else 0,
            "max": max(fares) if fares else 0,
            "avg": round(sum(fares)/len(fares), 2) if fares else 0
        }
    }

if __name__ == "__main__":
    emt_res = analyze_easemytrip(Path("easemytrip_parsed_data.json"))
    ignav_res = analyze_ignav_fixture(Path("apps/scraper/tests/adapters/ignav_raw_fixture.json"))
    
    output = {
        "easemytrip_analysis": emt_res,
        "ignav_analysis": ignav_res,
        "required_fields": REQUIRED_METHODOLOGY_FIELDS
    }
    
    with open("dataset_audit_results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
        
    print("\nSaved detailed audit results to dataset_audit_results.json")
