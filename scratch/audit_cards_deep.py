from bs4 import BeautifulSoup
from pathlib import Path
from collections import Counter

p_128 = Path("runtime/evidence/2026-09-26/source=easemytrip/run=b94ccc79-a511-4181-9501-61461d8d7ba3/page.html")
p_96 = Path("runtime/evidence/2026-09-26/source=easemytrip/run=96d98f81-a3d3-465d-8caa-b8cbdaeaebb9/page.html")

soup_128 = BeautifulSoup(p_128.read_text(encoding="utf-8", errors="ignore"), "html.parser")
soup_96 = BeautifulSoup(p_96.read_text(encoding="utf-8", errors="ignore"), "html.parser")

cards_128 = soup_128.select(".nw_listing_bx")
cards_96 = soup_96.select(".nw_listing_bx")

print(f"cards_128 total: {len(cards_128)}")
print(f"cards_96 total: {len(cards_96)}")

# Let's check card parsing on cards_128:
def inspect_cards(cards, label):
    rejections = Counter()
    accepted = []
    for idx, card in enumerate(cards):
        airline_el = card.select_one(".air_nmm_txt h6")
        flight_num_el = card.select_one(".air_nmm_txt span")
        dep_time_el = card.select_one(".tm_lc.texrgt h4")
        arr_time_el = card.select_one(".tm_lc:not(.texrgt) h4")
        price_el = card.select_one("h4[id^='spnPrice']")

        airline = airline_el.get_text(strip=True) if airline_el else None
        dep_str = dep_time_el.get_text(strip=True) if dep_time_el else ""
        arr_str = arr_time_el.get_text(strip=True) if arr_time_el else ""
        price_raw = price_el.get_text(strip=True) if price_el else ""
        price_clean = price_raw.replace(",", "").replace("₹", "").replace("Rs", "").strip()

        if "skeleton" in card.get("class", []):
            rejections["SKELETON_CARD"] += 1
        elif not airline or airline == "UNKNOWN":
            rejections["MISSING_AIRLINE"] += 1
        elif not dep_str or ":" not in dep_str:
            rejections["MISSING_DEPARTURE"] += 1
        elif not arr_str or ":" not in arr_str:
            rejections["MISSING_ARRIVAL"] += 1
        elif not price_clean:
            rejections["MISSING_PRICE"] += 1
        else:
            try:
                p = float(price_clean)
                if p <= 0:
                    rejections["ZERO_PRICE"] += 1
                else:
                    accepted.append((airline, flight_num_el.get_text(strip=True) if flight_num_el else None, p))
            except ValueError:
                rejections["INVALID_PRICE"] += 1
    print(f"\n[{label}] Accepted: {len(accepted)}, Rejections: {dict(rejections)}")
    return accepted, rejections

acc_128, rej_128 = inspect_cards(cards_128, "Run 128")
acc_96, rej_96 = inspect_cards(cards_96, "Run 96")

# Airline breakdown in 128 vs 96:
print("Airlines in 128:", Counter(x[0] for x in acc_128))
print("Airlines in 96:", Counter(x[0] for x in acc_96))
