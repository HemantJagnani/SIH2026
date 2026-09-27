import json
from pathlib import Path
from datetime import date
from uuid import uuid4
from collections import Counter, defaultdict

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

p_383 = Path("runtime/evidence/2026-09-26/source=easemytrip/run=a2f475ae-4704-4d29-993f-c99cfb2a5826/page.html")
p_128 = Path("runtime/evidence/2026-09-26/source=easemytrip/run=b94ccc79-a511-4181-9501-61461d8d7ba3/page.html")
p_96 = Path("runtime/evidence/2026-09-26/source=easemytrip/run=96d98f81-a3d3-465d-8caa-b8cbdaeaebb9/page.html")

html_383 = p_383.read_text(encoding="utf-8", errors="ignore")
html_128 = p_128.read_text(encoding="utf-8", errors="ignore")
html_96 = p_96.read_text(encoding="utf-8", errors="ignore")

obs_383 = parse_dom(html_383, req, uuid4(), "easemytrip", include_fare_options=True)
obs_100 = parse_dom(html_96, req, uuid4(), "easemytrip", include_fare_options=False)
obs_128 = parse_dom(html_128, req, uuid4(), "easemytrip", include_fare_options=False)

print("=== PHASE 1 & 3: ITINERARIES AND OFFERS IN obs_383 ===")
# Define itinerary fingerprint:
# origin, destination, travel_date, airline, flight_number, departure, arrival, stops
itin_map = defaultdict(list)
offer_fingerprints = []
dup_offers = []

for o in obs_383:
    itin_fp = (
        o.origin,
        o.destination,
        str(o.travel_date),
        o.airline,
        o.flight_number,
        o.departure_time_local.isoformat() if o.departure_time_local else None,
        o.arrival_time_local.isoformat() if o.arrival_time_local else None,
        o.stops
    )
    itin_map[itin_fp].append(o)
    
    # Offer fingerprint adds: fare_family, cabin, total_fare
    offer_fp = (
        itin_fp,
        o.fare_family,
        str(o.cabin),
        float(o.total_fare)
    )
    if offer_fp in offer_fingerprints:
        dup_offers.append(offer_fp)
    else:
        offer_fingerprints.append(offer_fp)

unique_itineraries = len(itin_map)
total_offers = len(obs_383)
unique_offers = len(offer_fingerprints)
print(f"Total observations in obs_383: {total_offers}")
print(f"Unique itineraries in obs_383: {unique_itineraries}")
print(f"Unique fare offers in obs_383: {unique_offers}")
print(f"Duplicate fare offers: {len(dup_offers)}")

# Offers per itinerary
offers_per_itin_counts = [len(v) for v in itin_map.values()]
print(f"Min offers per itin: {min(offers_per_itin_counts)}, Max: {max(offers_per_itin_counts)}, Avg: {sum(offers_per_itin_counts)/len(offers_per_itin_counts):.2f}")
print("Offers per itin distribution:", Counter(offers_per_itin_counts))

# Distributions
airline_counts = Counter(o.airline for o in obs_383)
print(f"Airline distribution in obs_383: {dict(airline_counts)}")

stops_counts = Counter(o.stops for o in obs_383)
print(f"Stops distribution in obs_383: {dict(stops_counts)}")

fare_family_counts = Counter(o.fare_family for o in obs_383)
print(f"Fare family distribution in obs_383: {dict(fare_family_counts)}")

# Price band distribution
def price_band(p):
    if p < 5000: return "<5000"
    if p < 7000: return "5000-7000"
    if p < 10000: return "7000-10000"
    if p < 15000: return "10000-15000"
    return ">15000"

price_bands = Counter(price_band(o.total_fare) for o in obs_383)
print(f"Price band distribution in obs_383: {dict(price_bands)}")

# Departure band distribution
def dep_band(dt):
    if not dt: return "UNKNOWN"
    h = dt.hour
    if 5 <= h < 12: return "Morning (05-12)"
    if 12 <= h < 17: return "Afternoon (12-17)"
    if 17 <= h < 21: return "Evening (17-21)"
    return "Night (21-05)"

dep_bands = Counter(dep_band(o.departure_time_local) for o in obs_383)
print(f"Departure band distribution: {dict(dep_bands)}")

print("\n=== PHASE 2: REJECTION ANALYSIS (128 vs 100) ===")
# Let's inspect the cards in p_128 (128 cards) vs p_96 (100 cards)
# What are the 28 cards present in 128 that are not in 100?
itin_100 = set((o.airline, o.flight_number, o.departure_time_local.strftime("%H:%M") if o.departure_time_local else None, o.arrival_time_local.strftime("%H:%M") if o.arrival_time_local else None) for o in obs_100)
itin_128 = set((o.airline, o.flight_number, o.departure_time_local.strftime("%H:%M") if o.departure_time_local else None, o.arrival_time_local.strftime("%H:%M") if o.arrival_time_local else None) for o in obs_128)

diff_128_100 = itin_128 - itin_100
print(f"Number of itineraries in 128 not in 100: {len(diff_128_100)}")
print("Airlines in diff:", Counter(x[0] for x in diff_128_100))

# Also check inside html_96: why were there 100 cards instead of 128?
# Did html_96 have skeleton cards or hidden cards or did the live page load 100 cards initially before scrolling?
soup_96 = BeautifulSoup(html_96, "html.parser")
all_divs_96 = soup_96.find_all("div")
cards_div_96 = [d for d in all_divs_96 if d.get("class") and "nw_listing_bx" in d.get("class")]
hidden_cards = [d for d in cards_div_96 if "display:none" in d.get("style", "").replace(" ", "").lower()]
print(f"In run 96: total nw_listing_bx={len(cards_div_96)}, hidden={len(hidden_cards)}")

# Check if there are other card classes or error/sold out cards in html_96:
sold_out = soup_96.select(".sold_out, .not_available, .no_seat")
print(f"Sold out tags in 96: {len(sold_out)}")
