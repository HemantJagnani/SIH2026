import re
from bs4 import BeautifulSoup
from pathlib import Path

html_96 = Path("runtime/evidence/2026-09-26/source=easemytrip/run=96d98f81-a3d3-465d-8caa-b8cbdaeaebb9/page.html").read_text(encoding="utf-8", errors="ignore")
html_128 = Path("runtime/evidence/2026-09-26/source=easemytrip/run=b94ccc79-a511-4181-9501-61461d8d7ba3/page.html").read_text(encoding="utf-8", errors="ignore")

# 1. Investigate 300 regex matches in html_96
soup_96 = BeautifulSoup(html_96, "html.parser")
cards_96 = soup_96.find_all("div", class_=lambda c: c and "nw_listing_bx" in c)
print(f"find_all('div', class_=...nw_listing_bx...): {len(cards_96)}")

# Check if there are other nw_listing_bx occurrences in script, style, comments, etc.
scripts = soup_96.find_all("script")
script_matches = sum(len(re.findall(r'nw_listing_bx', s.get_text())) for s in scripts)
print(f"nw_listing_bx occurrences inside <script>: {script_matches}")

comments = soup_96.find_all(string=lambda t: isinstance(t, type(soup_96.comment)) if hasattr(soup_96, 'comment') else False)
print(f"Comments: {len(comments)}")

# Let's inspect where all regex matches come from:
lines = html_96.splitlines()
matching_lines = []
for idx, line in enumerate(lines):
    if "nw_listing_bx" in line:
        matching_lines.append((idx, line[:100]))

print(f"Total lines with nw_listing_bx: {len(matching_lines)}")
if len(matching_lines) > 0:
    print("First 5 lines:", matching_lines[:5])
    print("Last 5 lines:", matching_lines[-5:])

# 2. Compare cards between run_96 (100) and run_128 (128)
soup_128 = BeautifulSoup(html_128, "html.parser")
cards_128 = soup_128.find_all("div", class_=lambda c: c and "nw_listing_bx" in c)

def get_flight_info(card):
    airline = card.select_one(".air_nmm_txt h6")
    flight_num = card.select_one(".air_nmm_txt span")
    dep = card.select_one(".tm_lc.texrgt h4")
    arr = card.select_one(".tm_lc:not(.texrgt) h4")
    price = card.select_one("h4[id^='spnPrice']")
    return (
        airline.get_text(strip=True) if airline else "NO_AIRLINE",
        flight_num.get_text(strip=True) if flight_num else "NO_NUM",
        dep.get_text(strip=True) if dep else "NO_DEP",
        arr.get_text(strip=True) if arr else "NO_ARR",
        price.get_text(strip=True) if price else "NO_PRICE"
    )

info_96 = [get_flight_info(c) for c in cards_96]
info_128 = [get_flight_info(c) for c in cards_128]

set_96 = set(info_96)
set_128 = set(info_128)

print(f"\nUnique in 96: {len(set_96)} out of {len(info_96)}")
print(f"Unique in 128: {len(set_128)} out of {len(info_128)}")
diff_128_minus_96 = set_128 - set_96
print(f"Cards in 128 but NOT in 96: {len(diff_128_minus_96)}")
for item in list(diff_128_minus_96)[:10]:
    print("  ", item)
