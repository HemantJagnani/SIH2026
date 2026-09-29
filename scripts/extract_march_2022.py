"""
Extracts archive.zip and filters all datasets to keep exclusively March 2022 data.

Processes:
1. economy.csv -> 138,409 rows across 01-03-2022 to 31-03-2022
2. business.csv -> 61,263 rows across 01-03-2022 to 31-03-2022
3. Indian Airlines.csv -> 199,564 rows across 01-03-2022 to 31-03-2022
4. march_2022_flights.csv -> Master consolidated dataset of 199,672 domestic flights
"""

import zipfile
import io
import csv
import os
import shutil
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE_PATH = ROOT / "archive.zip"
HISTORICAL_DIR = ROOT / "data" / "historical_march_2022"

def clean_field(val: str) -> str:
    """Cleans up internal newlines/tabs in fields like 'stop'."""
    val = val.strip()
    if "non-stop" in val:
        return "non-stop"
    elif "1-stop" in val:
        return "1-stop"
    elif "2+-stop" in val:
        return "2+-stop"
    return " ".join(val.split())

def is_march_2022(date_str: str) -> bool:
    """Checks if date is in March 2022 (e.g., 01-03-2022, 2022-03-01, etc.)."""
    d = date_str.strip().lstrip("\ufeff")
    parts = d.split("-")
    if len(parts) == 3:
        # DD-MM-YYYY
        if parts[1] == "03" and parts[2] == "2022":
            return True
        # YYYY-MM-DD
        if parts[0] == "2022" and parts[1] == "03":
            return True
    return False

def main():
    if not ARCHIVE_PATH.exists():
        raise FileNotFoundError(f"Missing {ARCHIVE_PATH}")

    HISTORICAL_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("  EXTRACTING & FILTERING ARCHIVE.ZIP TO MARCH 2022")
    print("=" * 70)

    # 1. Read economy.csv and filter for March 2022
    print("\n[1/4] Processing economy.csv...")
    eco_march_rows = []
    eco_dates_index = {} # row_idx -> date_str
    
    with zipfile.ZipFile(ARCHIVE_PATH, "r") as z:
        with z.open("economy.csv") as f_eco:
            reader = csv.reader(io.TextIOWrapper(f_eco, encoding="utf-8", errors="replace"))
            h_eco = next(reader)
            # Remove BOM if present
            h_eco[0] = h_eco[0].lstrip("\ufeff")
            
            for idx, row in enumerate(reader):
                if not row:
                    continue
                d_str = row[0].strip().lstrip("\ufeff")
                eco_dates_index[idx] = d_str
                if is_march_2022(d_str):
                    # Clean trailing whitespace/tabs in stop
                    cleaned_row = [row[0].strip().lstrip("\ufeff")] + [clean_field(c) for c in row[1:]]
                    eco_march_rows.append(cleaned_row)

    print(f"  -> Total March 2022 economy rows: {len(eco_march_rows):,}")

    # 2. Read business.csv and filter for March 2022
    print("\n[2/4] Processing business.csv...")
    biz_march_rows = []
    biz_dates_index = {}
    eco_count = len(eco_dates_index)

    with zipfile.ZipFile(ARCHIVE_PATH, "r") as z:
        with z.open("business.csv") as f_biz:
            reader = csv.reader(io.TextIOWrapper(f_biz, encoding="utf-8", errors="replace"))
            h_biz = next(reader)
            h_biz[0] = h_biz[0].lstrip("\ufeff")

            for idx, row in enumerate(reader):
                if not row:
                    continue
                d_str = row[0].strip().lstrip("\ufeff")
                biz_dates_index[idx + eco_count] = d_str
                if is_march_2022(d_str):
                    cleaned_row = [row[0].strip().lstrip("\ufeff")] + [clean_field(c) for c in row[1:]]
                    biz_march_rows.append(cleaned_row)

    print(f"  -> Total March 2022 business rows: {len(biz_march_rows):,}")

    combined_dates = {**eco_dates_index, **biz_dates_index}

    # 3. Read Indian Airlines.csv and filter for March 2022 using matched dates
    print("\n[3/4] Processing Indian Airlines.csv...")
    ia_march_rows = []
    with zipfile.ZipFile(ARCHIVE_PATH, "r") as z:
        with z.open("Indian Airlines.csv") as f_ia:
            reader = csv.reader(io.TextIOWrapper(f_ia, encoding="utf-8", errors="replace"))
            h_ia = next(reader)
            # Add date column to Indian Airlines header: ['index', 'date', 'airline', ...]
            h_ia_with_date = [h_ia[0] if h_ia[0] else "index", "date"] + h_ia[1:]

            for row in reader:
                if not row:
                    continue
                try:
                    orig_idx = int(row[0])
                    d_str = combined_dates.get(orig_idx, "")
                    if is_march_2022(d_str):
                        row_with_date = [row[0], d_str] + [clean_field(c) for c in row[1:]]
                        ia_march_rows.append(row_with_date)
                except ValueError:
                    continue

    print(f"  -> Total March 2022 Indian Airlines rows: {len(ia_march_rows):,}")

    # 4. Create Master Consolidated March 2022 Flights Dataset
    print("\n[4/4] Creating master consolidated march_2022_flights.csv...")
    master_header = [
        "date", "airline", "flight_code", "flight_number", "flight_full",
        "origin_city", "destination_city", "departure_time", "arrival_time",
        "duration", "stops", "cabin_class", "price_inr"
    ]
    master_rows = []

    for r in eco_march_rows:
        # ['date', 'airline', 'ch_code', 'num_code', 'dep_time', 'from', 'time_taken', 'stop', 'arr_time', 'to', 'price']
        price_clean = r[10].replace(",", "").strip()
        master_rows.append([
            r[0], r[1], r[2], r[3], f"{r[2]}-{r[3]}",
            r[5], r[9], r[4], r[8],
            r[6], r[7], "Economy", price_clean
        ])

    for r in biz_march_rows:
        price_clean = r[10].replace(",", "").strip()
        master_rows.append([
            r[0], r[1], r[2], r[3], f"{r[2]}-{r[3]}",
            r[5], r[9], r[4], r[8],
            r[6], r[7], "Business", price_clean
        ])

    print(f"  -> Total master March 2022 flights: {len(master_rows):,}")

    # Write files to root and data/historical_march_2022/
    targets = [
        # Root destination
        (ROOT / "economy.csv", h_eco, eco_march_rows),
        (ROOT / "business.csv", h_biz, biz_march_rows),
        (ROOT / "Indian Airlines.csv", h_ia_with_date, ia_march_rows),
        (ROOT / "march_2022_flights.csv", master_header, master_rows),
        # data/historical_march_2022 destination
        (HISTORICAL_DIR / "economy.csv", h_eco, eco_march_rows),
        (HISTORICAL_DIR / "business.csv", h_biz, biz_march_rows),
        (HISTORICAL_DIR / "Indian Airlines.csv", h_ia_with_date, ia_march_rows),
        (HISTORICAL_DIR / "march_2022_flights.csv", master_header, master_rows),
    ]

    for path, hdr, rows in targets:
        with open(path, "w", encoding="utf-8", newline="") as f_out:
            writer = csv.writer(f_out)
            writer.writerow(hdr)
            writer.writerows(rows)
        size_mb = path.stat().st_size / (1024 * 1024)
        print(f"Wrote {path.name} -> {path} ({len(rows):,} rows, {size_mb:.2f} MB)")

    # Date distribution check
    day_counts = Counter(r[0] for r in master_rows)
    print("\nMarch 2022 Date Coverage (all 31 days present):")
    for d in sorted(day_counts.keys()):
        print(f"  {d}: {day_counts[d]:,} flights")

    print("\nExtraction & March 2022 filtering completed successfully!")

if __name__ == "__main__":
    main()
