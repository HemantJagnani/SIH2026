import json
from pathlib import Path
from datetime import date
from uuid import uuid4
from decimal import Decimal
from collections import Counter, defaultdict

from models.request import FareSearchRequest
from sources.easemytrip.parser import parse_dom

req = FareSearchRequest(
    origin="DEL",
    destination="BOM",
    travel_date=date(2026, 10, 3),
    lead_days=7,
    source="easemytrip",
    collection_mode="BROWSER"
)

p_383 = Path("runtime/evidence/2026-09-26/source=easemytrip/run=a2f475ae-4704-4d29-993f-c99cfb2a5826/page.html")
html_383 = p_383.read_text(encoding="utf-8", errors="ignore")
obs_383 = parse_dom(html_383, req, uuid4(), "easemytrip", include_fare_options=True)

# Group by unique itinerary fingerprint
# (airline, flight_number, dep_str, arr_str, stops)
itin_to_offers = defaultdict(list)
for o in obs_383:
    dep_str = o.departure_time_local.strftime("%H:%M") if o.departure_time_local else "UNKNOWN"
    arr_str = o.arrival_time_local.strftime("%H:%M") if o.arrival_time_local else "UNKNOWN"
    key = (o.airline, o.flight_number, dep_str, arr_str, o.stops)
    itin_to_offers[key].append(o)

print(f"Total itineraries: {len(itin_to_offers)}")

def get_time_band(dep_str):
    h = int(dep_str.split(":")[0])
    if 5 <= h < 12: return "Morning"
    if 12 <= h < 17: return "Afternoon"
    if 17 <= h < 21: return "Evening"
    return "Night"

def get_price_band(min_price):
    if min_price < 7000: return "Low"
    if min_price <= 12000: return "Mid"
    return "High"

# Decorate itineraries
decorated_itins = []
for key, offers in sorted(itin_to_offers.items(), key=lambda x: (x[0][0], x[0][1], x[0][2])):
    airline, flight_num, dep_str, arr_str, stops = key
    min_price = min(o.total_fare for o in offers)
    time_band = get_time_band(dep_str)
    price_band = get_price_band(min_price)
    stop_type = "Nonstop" if stops == 0 else "1-stop"
    
    decorated_itins.append({
        "key": key,
        "airline": airline,
        "flight_number": flight_num,
        "dep_time": dep_str,
        "arr_time": arr_str,
        "stops": stops,
        "stop_type": stop_type,
        "time_band": time_band,
        "price_band": price_band,
        "min_price": min_price,
        "offers_count": len(offers),
        "offers": offers
    })

# Deterministic selection:
# We want 20 itineraries covering:
# - All 5 airlines: IndiGo, Air India, Air India Express, AkasaAir, SpiceJet
# - Both stop types: Nonstop, 1-stop
# - All time bands: Morning, Afternoon, Evening, Night
# - All price bands: Low, Mid, High

# Sort deterministically
decorated_itins.sort(key=lambda x: (x["airline"], x["stop_type"], x["time_band"], x["price_band"], x["dep_time"]))

selected = []
seen_signatures = set()

# First pass: pick 1 from each airline
airlines = ["IndiGo", "Air India", "Air India Express", "AkasaAir", "SpiceJet"]
for al in airlines:
    matches = [it for it in decorated_itins if it["airline"] == al]
    if matches:
        selected.append(matches[0])
        seen_signatures.add(matches[0]["key"])

# Second pass: pick combinations of (stop_type, time_band, price_band)
for it in decorated_itins:
    if len(selected) >= 20:
        break
    if it["key"] in seen_signatures:
        continue
    # Check if this adds diversity
    sig = (it["airline"], it["stop_type"], it["time_band"], it["price_band"])
    if sig not in [ (s["airline"], s["stop_type"], s["time_band"], s["price_band"]) for s in selected ]:
        selected.append(it)
        seen_signatures.add(it["key"])

# If still under 20, fill with remaining
for it in decorated_itins:
    if len(selected) >= 20:
        break
    if it["key"] not in seen_signatures:
        selected.append(it)
        seen_signatures.add(it["key"])

print(f"Selected sample size: {len(selected)}")
print("Sample distribution:")
print("  Airlines:", Counter(s["airline"] for s in selected))
print("  Stops:", Counter(s["stop_type"] for s in selected))
print("  Time bands:", Counter(s["time_band"] for s in selected))
print("  Price bands:", Counter(s["price_band"] for s in selected))

for i, s in enumerate(selected, 1):
    print(f"{i}. {s['airline']} {s['flight_number']} ({s['dep_time']}-{s['arr_time']}, {s['stop_type']}) - {s['time_band']} | {s['price_band']} (₹{s['min_price']}) -> {s['offers_count']} offers")
