from bs4 import BeautifulSoup
from pathlib import Path

html_p = Path("runtime/evidence/2026-09-26/source=easemytrip/run=b94ccc79-a511-4181-9501-61461d8d7ba3/page.html")
soup = BeautifulSoup(html_p.read_text(encoding="utf-8", errors="ignore"), "html.parser")
card = soup.select_one(".nw_listing_bx")

# Let's inspect siblings or children near a.d-up
link = card.select_one("a.d-up")
parent = link.parent if link else None
print("Link parent tag:", parent.name if parent else None, parent.get("class") if parent else None)

# Find all hidden or collapsed divs inside card
hidden = card.find_all(lambda tag: tag.name == "div" and (
    "dn" in tag.get("class", []) or
    "hide" in tag.get("class", []) or
    "hidden" in tag.get("class", []) or
    "display:none" in tag.get("style", "").replace(" ", "")
))
print(f"Hidden divs inside card: {len(hidden)}")
for h in hidden[:10]:
    cls = h.get("class")
    id_v = h.get("id")
    txt = h.get_text(separator=' | ', strip=True)[:100].encode('ascii', 'backslashreplace').decode('ascii')
    print(f"  Hidden div: id={id_v}, class={cls}, snippet='{txt}'")

# Check if there are segment details or aircraft in the card
air_craft_matches = card.find_all(string=lambda t: t and ("Boeing" in t or "Airbus" in t or "A320" in t or "B737" in t or "737" in t or "320" in t))
print("Aircraft matches:", [m.strip() for m in air_craft_matches])
