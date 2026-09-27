from pathlib import Path
from bs4 import BeautifulSoup

base_dir = Path("runtime/evidence/2026-09-26/source=easemytrip")
for run_dir in base_dir.glob("run=*"):
    html_file = run_dir / "page.html"
    result_file = run_dir / "result.json"
    req_file = run_dir / "request.json"
    if html_file.exists():
        html = html_file.read_text(encoding="utf-8", errors="ignore")
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select(".nw_listing_bx")
        skeletons = soup.select(".nw_listing_bx.skeleton")
        real_cards = soup.select(".nw_listing_bx:not(.skeleton)")
        res_info = result_file.read_text() if result_file.exists() else "None"
        req_info = req_file.read_text() if req_file.exists() else "None"
        print(f"Run {run_dir.name}: total={len(cards)}, skeletons={len(skeletons)}, real={len(real_cards)}")
        print(f"  Result: {res_info.strip()}")
        print(f"  Request: {req_info.strip()[:100]}")
