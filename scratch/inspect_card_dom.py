from bs4 import BeautifulSoup
from pathlib import Path
import re

html_p = Path("runtime/evidence/2026-09-26/source=easemytrip/run=b94ccc79-a511-4181-9501-61461d8d7ba3/page.html")
soup = BeautifulSoup(html_p.read_text(encoding="utf-8", errors="ignore"), "html.parser")
card = soup.select_one(".nw_listing_bx")

print("Card ID:", card.get("id"))
print("Card classes:", card.get("class"))

# Search for any buttons or links inside the card
buttons = card.select("button, a, span.cursor-pointer, .flt_det, [onclick]")
print(f"Total clickable-looking elements in card: {len(buttons)}")
for b in buttons[:20]:
    txt = b.get_text(strip=True)[:40].encode('ascii', 'backslashreplace').decode('ascii')
    cls = b.get("class")
    onc = b.get("onclick")
    id_val = b.get("id")
    print(f"  Tag: {b.name}, class: {cls}, id: {id_val}, text: '{txt}', onclick: '{onc}'")

# Search for "baggage", "fare breakup", "cancellation", "flight details" anywhere in page
text_snippets = {}
for term in ["baggage", "cabin", "check-in", "fare breakup", "base fare", "cancellation", "refundable", "flight details", "more fare"]:
    matches = soup.find_all(string=re.compile(term, re.IGNORECASE))
    print(f"Search for '{term}': {len(matches)} matches in page")
    if matches:
        sample_txt = matches[0].strip()[:80].encode('ascii', 'backslashreplace').decode('ascii')
        print(f"  Sample: '{sample_txt}'")

