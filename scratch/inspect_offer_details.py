from bs4 import BeautifulSoup
from pathlib import Path
import re

html_p = Path("runtime/evidence/2026-09-26/source=easemytrip/run=b94ccc79-a511-4181-9501-61461d8d7ba3/page.html")
soup = BeautifulSoup(html_p.read_text(encoding="utf-8", errors="ignore"), "html.parser")
card = soup.select_one(".nw_listing_bx")

# Let's inspect all fare option boxes in this first card
option_boxes = card.select("._mfarebx, label:has(.fareheader), div:has(> .fareheader)")
print(f"Option boxes in first card: {len(option_boxes)}")

for idx, ob in enumerate(option_boxes):
    header = ob.select_one(".fareheader")
    price = ob.select_one(".fareprice")
    hdr_txt = header.get_text(strip=True) if header else "NO_HDR"
    prc_txt = price.get_text(strip=True).encode('ascii', 'backslashreplace').decode('ascii') if price else "NO_PRC"
    print(f"\n--- Offer {idx+1}: {hdr_txt} ({prc_txt}) ---")
    
    # Check all text inside this offer box
    lines = [s.strip() for s in ob.stripped_strings if s.strip()]
    for line in lines:
        line_clean = line.encode('ascii', 'backslashreplace').decode('ascii')
        print(f"   {line_clean}")

# Also inspect the "Flight Details" section in the card
details_link = card.select_one("a.d-up, a:contains('Flight Details')")
print(f"\nDetails link: {details_link}")
# Check if there is a flight details container already inside the card DOM (e.g. .flt_det_bx or hidden div)
details_containers = card.select(".flt_det_bx, [class*='detail'], [id*='detail'], [class*='tab']")
print(f"Candidate details containers in card: {len(details_containers)}")
for dc in details_containers[:5]:
    cls = dc.get("class")
    id_val = dc.get("id")
    print(f"  Container: class={cls}, id={id_val}, text_len={len(dc.get_text(strip=True))}")
    snippet = dc.get_text(separator=' | ', strip=True)[:150].encode('ascii', 'backslashreplace').decode('ascii')
    print(f"    Snippet: {snippet}")
