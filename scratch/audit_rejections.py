import json
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import date
from models.request import FareSearchRequest
from validation.pipeline import validate_observation
from sources.easemytrip.parser import parse_dom
from uuid import uuid4

html_path = Path("runtime/evidence/2026-09-26/source=easemytrip/run=96d98f81-a3d3-465d-8caa-b8cbdaeaebb9/page.html")
if not html_path.exists():
    print(f"File not found: {html_path}")
    exit(1)

html = html_path.read_text(encoding="utf-8", errors="ignore")
soup = BeautifulSoup(html, "html.parser")
cards = soup.select(".nw_listing_bx")
print(f"Total .nw_listing_bx cards found: {len(cards)}")

skeleton_cards = soup.select(".nw_listing_bx.skeleton")
print(f"Skeleton cards: {len(skeleton_cards)}")

req = FareSearchRequest(
    origin="DEL",
    destination="BOM",
    travel_date=date(2026, 10, 3),
    lead_days=7,
)

rejections = {}
accepted_raw = []

for i, card in enumerate(cards):
    classes = card.get("class", [])
    # Check if skeleton
    if "skeleton" in classes:
        rejections["SKELETON_CARD"] = rejections.get("SKELETON_CARD", 0) + 1
        continue

    # Airline
    airline_el = card.select_one(".air_nmm_txt h6")
    airline = airline_el.get_text(strip=True) if airline_el else None

    # Flight number
    flight_num_el = card.select_one(".air_nmm_txt span")
    flight_num = flight_num_el.get_text(strip=True) if flight_num_el else None

    # Dep time
    dep_time_el = card.select_one(".tm_lc.texrgt h4")
    dep_str = dep_time_el.get_text(strip=True) if dep_time_el else ""

    # Arr time
    arr_time_el = card.select_one(".tm_lc:not(.texrgt) h4")
    arr_str = arr_time_el.get_text(strip=True) if arr_time_el else ""

    # Price
    price_el = card.select_one("h4[id^='spnPrice']")
    price_raw = price_el.get_text(strip=True) if price_el else ""
    price_clean = price_raw.replace(",", "").replace("₹", "").replace("Rs", "").strip()

    reason = None
    if not airline or airline == "UNKNOWN":
        reason = "MISSING_AIRLINE"
    elif not dep_str or ":" not in dep_str:
        reason = "MISSING_DEPARTURE"
    elif not arr_str or ":" not in arr_str:
        reason = "MISSING_ARRIVAL"
    elif not price_clean:
        reason = "MISSING_PRICE"
    else:
        try:
            val = float(price_clean)
            if val <= 0:
                reason = "INVALID_PRICE_ZERO"
        except ValueError:
            reason = "INVALID_PRICE_NAN"

    if reason:
        rejections[reason] = rejections.get(reason, 0) + 1
        print(f"Card {i} rejected in parser check: {reason}, classes={classes}, text snippet: {card.get_text(strip=True)[:60]}")
    else:
        accepted_raw.append((i, airline, flight_num, dep_str, arr_str, price_clean))

print(f"\nRaw accepted by parser check: {len(accepted_raw)}")
print(f"Rejections summary in parser: {rejections}")

# Now test through parse_dom and validation pipeline
run_id = uuid4()
parsed_obs = parse_dom(html, req, run_id, "easemytrip", include_fare_options=False)
print(f"\nParsed observations: {len(parsed_obs)}")

validation_rejections = {}
valid_obs = []
for obs in parsed_obs:
    validated, result = validate_observation(obs.model_dump(mode="json"))
    if result.is_valid and validated:
        valid_obs.append(validated)
    else:
        for err in result.errors:
            validation_rejections[err.field or "UNKNOWN"] = validation_rejections.get(err.field or "UNKNOWN", 0) + 1

print(f"Validation passed: {len(valid_obs)}")
print(f"Validation errors: {validation_rejections}")
