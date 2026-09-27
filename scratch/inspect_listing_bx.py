from bs4 import BeautifulSoup
from pathlib import Path

html_p = Path("runtime/evidence/2026-09-26/source=easemytrip/run=96d98f81-a3d3-465d-8caa-b8cbdaeaebb9/page.html")
soup = BeautifulSoup(html_p.read_text(encoding="utf-8", errors="ignore"), "html.parser")
cards = soup.select(".nw_listing_bx")
print("soup.select('.nw_listing_bx') length:", len(cards))

# Let's inspect tag names and IDs
tag_counts = {}
for c in cards:
    tag_counts[c.name] = tag_counts.get(c.name, 0) + 1
print("Tag counts:", tag_counts)

# Why did regex find 300?
import re
content = html_p.read_text(encoding="utf-8", errors="ignore")
matches = re.findall(r'<([a-zA-Z0-9]+)[^>]*class="[^"]*nw_listing_bx[^"]*"', content)
print("Regex match tags:", len(matches))
from collections import Counter
print(Counter(matches))

# Also inspect run=b94ccc79 (which had count 128) vs run=96d98f81 (count 100)
html_128 = Path("runtime/evidence/2026-09-26/source=easemytrip/run=b94ccc79-a511-4181-9501-61461d8d7ba3/page.html")
soup_128 = BeautifulSoup(html_128.read_text(encoding="utf-8", errors="ignore"), "html.parser")
cards_128 = soup_128.select(".nw_listing_bx")
print("Run b94ccc79 (128 run) soup length:", len(cards_128))
