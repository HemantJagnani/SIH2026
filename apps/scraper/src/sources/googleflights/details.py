import asyncio
import logging
from typing import List, Dict, Any
from sources.googleflights.selectors import GoogleFlightsSelectors

logger = logging.getLogger(__name__)

class GoogleFlightsDetailsExpander:
    def __init__(self, page):
        self.page = page

    async def expand_and_capture(self) -> List[str]:
        """
        Iterates over all flight cards on the page.
        Clicks to expand each card, captures the HTML of the details panel,
        and then closes it. Returns a list of HTML strings for each details panel.
        """
        detail_htmls = []
        try:
            # Find all buttons that expand flight details
            expand_buttons = self.page.locator(GoogleFlightsSelectors.EXPAND_CARD_BUTTON)
            count = await expand_buttons.count()
            logger.info(f"GoogleFlightsDetailsExpander: Found {count} expandable flight cards.")

            count = min(count, 1) # For testing, limit to 1
            for i in range(count):
                btn = expand_buttons.nth(i)
                
                # Check if it's visible and enabled
                if not await btn.is_visible():
                    continue

                try:
                    # Scroll into view
                    await btn.scroll_into_view_if_needed()
                    await asyncio.sleep(0.5)

                    # Click to expand
                    await btn.click(timeout=3000)
                    logger.debug(f"GoogleFlightsDetailsExpander: Clicked card {i+1}/{count}.")
                    
                    # Wait for the details panel to appear
                    details_panel = self.page.locator(GoogleFlightsSelectors.DETAILS_PANEL).nth(0) # or first visible
                    await details_panel.wait_for(state="visible", timeout=3000)
                    
                    # Also try to check for Fare Options if present (Select button)
                    # We could expand it, but for Phase B, just capturing the details panel is a good start
                    
                    # Capture HTML of the expanded card context (the whole li or just details panel)
                    # We'll capture the parent li so we have context (times, etc.) to correlate later.
                    parent_li = btn.locator("xpath=ancestor::li").first
                    html = await parent_li.inner_html()
                    detail_htmls.append(html)
                    
                    # Click again to collapse
                    await btn.click(timeout=3000)
                    await asyncio.sleep(0.5)

                except Exception as e:
                    logger.warning(f"GoogleFlightsDetailsExpander: Failed to expand card {i+1}: {e}")
                    # Try to recover by pressing Escape or clicking elsewhere
                    await self.page.keyboard.press("Escape")
                    await asyncio.sleep(0.5)

        except Exception as e:
            logger.error(f"GoogleFlightsDetailsExpander: Overall extraction error: {e}")

        return detail_htmls
