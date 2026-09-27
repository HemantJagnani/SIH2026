import json
from pathlib import Path
from datetime import date
from uuid import uuid4
from collections import Counter

from models.request import FareSearchRequest
from sources.easemytrip.parser import parse_dom
from bs4 import BeautifulSoup

req = FareSearchRequest(
    origin="DEL",
    destination="BOM",
    travel_date=date(2026, 10, 3),
    lead_days=7,
    source="easemytrip",
    collection_mode="BROWSER"
)

# Load run 96d98f81 (100 obs) and run b94ccc79 (128 obs) and run a2f475ae (383 obs)
p_96 = Path("runtime/evidence/2026-09-26/source=easemytrip/run=96d98f81-a3d3-465d-8caa-b8cbdaeaebb9/page.html")
p_128 = Path("runtime/evidence/2026-09-26/source=easemytrip/run=b94ccc79-a511-4181-9501-61461d8d7ba3/page.html")
p_383 = Path("runtime/evidence/2026-09-26/source=easemytrip/run=a2f475ae-4704-4d29-993f-c99cfb2a5826/page.html")

html_96 = p_96.read_text(encoding="utf-8", errors="ignore")
html_128 = p_128.read_text(encoding="utf-8", errors="ignore")
html_383 = p_383.read_text(encoding="utf-8", errors="ignore")

# Parse 383 run (CORE_AND_DETAILS)
obs_383 = parse_dom(html_383, req, uuid4(), "easemytrip", include_fare_options=True)
print(f"obs_383 count: {len(obs_383)}")

# Parse 96 run (CORE_ONLY)
obs_96 = parse_dom(html_96, req, uuid4(), "easemytrip", include_fare_options=False)
print(f"obs_96 count: {len(obs_96)}")

# Parse 128 run (CORE_ONLY)
obs_128 = parse_dom(html_128, req, uuid4(), "easemytrip", include_fare_options=False)
print(f"obs_128 count: {len(obs_128)}")

# Also parse 128 with include_fare_options=True
obs_128_details = parse_dom(html_128, req, uuid4(), "easemytrip", include_fare_options=True)
print(f"obs_128_details count: {len(obs_128_details)}")
