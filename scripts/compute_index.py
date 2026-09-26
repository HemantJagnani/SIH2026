"""
CLI runner for compiling the Indian Airfare Price Index (APIx) using the Phase 3 Engine.
Loads canonical normalized observations, processes monthly geometric prices,
computes elementary Jevons indices, and aggregates across lead times and routes.
"""

import json
from decimal import Decimal
from pathlib import Path
from models.canonical import NormalizedFareObservation
from index import APIxEngine

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    return str(obj)

def main():
    json_path = Path("easemytrip_normalized_data.json")
    if not json_path.exists():
        print(f"Error: {json_path} does not exist. Run scripts/normalize_dataset.py first.")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        records_json = json.load(f)

    observations = [NormalizedFareObservation(**r) for r in records_json]
    print(f"Loaded {len(observations)} canonical normalized observations.")

    engine = APIxEngine()
    result = engine.process_period(period="2026-09", observations=observations)

    out_file = Path("apix_compiled_index.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result.model_dump(mode="json"), f, indent=2, default=decimal_default)

    print(f"\n========================================================")
    print(f"  {result.index_name}")
    print(f"  Period: {result.period} | Base: {result.reference_period}=100")
    print(f"  All-India APIx Value: {result.index_value}")
    print(f"  Route Indices:")
    for route, val in result.route_indices.items():
        print(f"    - {route}: {val}")
    print(f"  Lead-Time Indices:")
    for lt, val in result.lead_time_indices.items():
        print(f"    - {lt}: {val}")
    print(f"  Methodology Version: {result.methodology_version}")
    print(f"  Weight Version:      {result.weight_version}")
    print(f"========================================================")
    print(f"Results saved to {out_file.absolute()}")

if __name__ == "__main__":
    main()
