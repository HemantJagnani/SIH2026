import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        # Use mrscraper proxy!
        browser = await p.chromium.launch(
            headless=False,
            proxy={
                "server": "http://proxy.mrscraper.com:10000",
                "username": "hjagnani64gmailcom",
                "password": "b5gGb0GFHiv11"
            }
        )
        page = await browser.new_page()
        
        url = "https://flight.easemytrip.com/FlightList/Index?srch=DEL-City|BOM-City|29/09/2026&px=1-0-0&cbn=0&CCode=IN&crn=INR"
        print(f"Navigating to {url}")
        
        await page.goto(url)
        
        print("Waiting up to 60 seconds for flight cards to load...")
        try:
            await page.wait_for_selector(".flt-res-card, .row.top-srh, .main-card, #row0", timeout=60000)
            print("Flights loaded successfully!")
            
            # Print first 5 flights
            cards = await page.query_selector_all(".flt-res-card, .row.top-srh, .main-card")
            print(f"Found {len(cards)} flight cards.")
            
            for i, card in enumerate(cards[:5]):
                text = await card.inner_text()
                print(f"--- Flight {i+1} ---")
                print(text.replace("\n", " ")[:100])
                
        except Exception as e:
            print(f"Timeout waiting for flights: {e}")
            
        # Try to extract data if loaded, otherwise just take screenshot
        await page.screenshot(path="test_easemytrip.png")
        print("Saved screenshot to test_easemytrip.png")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
