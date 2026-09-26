"""
Runs canonical normalization on easemytrip_parsed_data.json and exports easemytrip_normalized_data.json.
"""

import json
from pathlib import Path
from normalization.pipeline import normalize_dataset

def main():
    in_path = Path("easemytrip_parsed_data.json")
    if not in_path.exists():
        print(f"Error: {in_path} does not exist.")
        return

    with open(in_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    print(f"Loaded {len(records)} raw records from {in_path}")
    normalized = normalize_dataset(records)
    print(f"Successfully normalized {len(normalized)} records.")

    out_path = Path("easemytrip_normalized_data.json")
    data = [obs.model_dump(mode="json") for obs in normalized]

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"Exported canonical normalized observations to {out_path.absolute()}")

    # Print summary
    valid = sum(1 for o in normalized if o.quality_status == "VALID")
    dups = sum(1 for o in normalized if o.quality_status == "DUPLICATE")
    strata = len(set(o.product_stratum_id for o in normalized))
    itins = len(set(o.itinerary_fingerprint for o in normalized))
    print(f"Summary: {valid} VALID, {dups} DUPLICATES, {strata} unique Product Strata, {itins} unique Itineraries.")

if __name__ == "__main__":
    main()
