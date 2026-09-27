import json
from pathlib import Path
import re

runs = [
    "run=96d98f81-a3d3-465d-8caa-b8cbdaeaebb9",
    "run=b94ccc79-a511-4181-9501-61461d8d7ba3",
    "run=a2f475ae-4704-4d29-993f-c99cfb2a5826",
    "run=e0e06457-8e32-49ba-8b0c-7626332627de",
    "run=5415f736-386b-4aea-95c6-fe97472114ea"
]

base_dir = Path("runtime/evidence/2026-09-26/source=easemytrip")
for r in runs:
    p = base_dir / r
    res_f = p / "result.json"
    req_f = p / "request.json"
    html_f = p / "page.html"
    print("--------------------------------------------------")
    print(f"Run: {r}")
    if req_f.exists():
        print(f"Request: {req_f.read_text().strip()}")
    if res_f.exists():
        print(f"Result: {res_f.read_text().strip()}")
    if html_f.exists():
        content = html_f.read_text(encoding="utf-8", errors="ignore")
        bx_all = len(re.findall(r'class="[^"]*nw_listing_bx[^"]*"', content))
        bx_skel = len(re.findall(r'class="[^"]*nw_listing_bx[^"]*skeleton[^"]*"', content))
        bx_real = bx_all - bx_skel
        print(f"HTML: size={len(content)} bytes, nw_listing_bx total={bx_all}, skeleton={bx_skel}, non-skeleton={bx_real}")
