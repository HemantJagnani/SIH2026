import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        # Use mrscraper proxy!
        browser = await p.chromium.launch(
            headless=True,
            proxy={
                "server": "http://proxy.mrscraper.com:10000",
                "username": "hjagnani64gmailcom",
                "password": "b5gGb0GFHiv11"
            }
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768},
            locale="en-IN",
            timezone_id="Asia/Kolkata",
        )
        page = await context.new_page()
        
        # Test route: DEL to BOM with full city-country format
        url = "https://flight.easemytrip.com/FlightList/Index?srch=DEL-Delhi-India|BOM-Mumbai-India|10/10/2026&px=1-0-0&cbn=0&CCode=IN&crn=INR"
        print(f"Navigating to {url}")
        
        page.on("response", lambda r: print(f"[NET {r.status}] {r.url[:80]}") if "flight" in r.url.lower() or "search" in r.url.lower() or "api" in r.url.lower() else None)

        try:
            await page.goto(url, timeout=60000)
            print(f"Page loaded: {await page.title()}")
        except Exception as e:
            print(f"Goto error: {e}")
        
        print("Waiting up to 60 seconds for .fltResult flight cards...")
        try:
            await page.wait_for_selector(".fltResult", timeout=60000)
            print("Flight cards selector .fltResult detected!")
            
            cards = await page.query_selector_all(".fltResult")
            print(f"Found {len(cards)} flight cards.")
            for i, card in enumerate(cards[:5]):
                fn = await card.get_attribute("fn")
                airline = await card.get_attribute("aircode")
                price = await card.get_attribute("price")
                deptm = await card.get_attribute("deptm")
                arrtm = await card.get_attribute("arrtm")
                stops = await card.get_attribute("stop")
                print(f"--- Flight {i+1}: {airline} {fn} | Rs.{price} | {deptm} -> {arrtm} | {stops} stop(s) ---")
        except Exception as e:
            print(f"Timeout/Error waiting for flights: {e}")
            
        dom = await page.content()
        with open("test_easemytrip_dom.html", "w", encoding="utf-8") as f:
            f.write(dom)
        print(f"Saved DOM ({len(dom)} bytes) to test_easemytrip_dom.html")

        await page.screenshot(path="test_easemytrip.png")
        print("Saved screenshot to test_easemytrip.png")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
