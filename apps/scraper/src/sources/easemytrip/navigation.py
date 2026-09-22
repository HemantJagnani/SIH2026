import asyncio
import logging
import time
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)

class NavigationState(Enum):
    INIT = "INIT"
    POLICY_CHECK = "POLICY_CHECK"
    LOAD_SEARCH_PAGE = "LOAD_SEARCH_PAGE"
    PAGE_READY = "PAGE_READY"
    FILL_ORIGIN = "FILL_ORIGIN"
    FILL_DESTINATION = "FILL_DESTINATION"
    SELECT_TRAVEL_DATE = "SELECT_TRAVEL_DATE"
    SET_PASSENGERS = "SET_PASSENGERS"
    SUBMIT_SEARCH = "SUBMIT_SEARCH"
    WAIT_FOR_RESULTS = "WAIT_FOR_RESULTS"
    RESULTS_DETECTED = "RESULTS_DETECTED"
    
    # Terminal/Failure states
    EMPTY_RESULTS = "EMPTY_RESULTS"
    PROTECTION_DETECTED = "PROTECTION_DETECTED"
    CAPTCHA_DETECTED = "CAPTCHA_DETECTED"
    SEARCH_ERROR = "SEARCH_ERROR"
    TIMEOUT = "TIMEOUT"

class SearchResultContext:
    def __init__(self):
        self.terminal_state: Optional[NavigationState] = None
        self.network_response: Optional[dict] = None
        self.rendered_dom: Optional[str] = None
        self.evidence: dict = {}

class EaseMyTripNavigation:
    def __init__(self, page, request):
        self.page = page
        self.request = request
        self.context = SearchResultContext()
        self.state = NavigationState.INIT
        
    async def execute(self) -> SearchResultContext:
        """Run the state machine."""
        while True:
            try:
                if self.state == NavigationState.INIT:
                    self.state = NavigationState.LOAD_SEARCH_PAGE
                
                elif self.state == NavigationState.LOAD_SEARCH_PAGE:
                    logger.info("EaseMyTripNavigation: Loading search results page directly...")
                    # Format: https://flight.easemytrip.com/FlightList/Index?srch=DEL-Delhi-India|BOM-Mumbai-India|29/09/2026&px=1-0-0&cbn=0&CCode=IN&crn=INR
                    travel_date_str = self.request.travel_date.strftime("%d/%m/%Y")
                    url = f"https://flight.easemytrip.com/FlightList/Index?srch={self.request.origin}-City|{self.request.destination}-City|{travel_date_str}&px=1-0-0&cbn=0&CCode=IN&crn=INR"
                    logger.info(f"Navigating to {url}")
                    await self.page.goto(url)
                    self.state = NavigationState.PAGE_READY
                    
                elif self.state == NavigationState.PAGE_READY:
                    logger.info("EaseMyTripNavigation: Waiting for page to be ready...")
                    await self.page.wait_for_load_state("domcontentloaded")
                    # Check for bot protection early
                    if await self._is_protection_detected():
                        self.state = NavigationState.PROTECTION_DETECTED
                    else:
                        self.state = NavigationState.WAIT_FOR_RESULTS
                    
                elif self.state == NavigationState.WAIT_FOR_RESULTS:
                    logger.info("EaseMyTripNavigation: Waiting for results (up to 60 seconds)...")
                    
                    # Capture API responses to see where the data comes from!
                    async def handle_response(response):
                        if "api" in response.url.lower() or "flight" in response.url.lower() or "search" in response.url.lower():
                            logger.info(f"NETWORK RESPONSE: {response.url} - {response.status}")
                            if "json" in response.headers.get("content-type", "").lower():
                                try:
                                    logger.info(f"JSON DATA: {str(await response.json())[:500]}")
                                except:
                                    pass
                    
                    self.page.on("response", handle_response)
                    
                    try:
                        # Add a small buffer for bot protection redirects before checking DOM
                        await asyncio.sleep(5)
                        # Wait for either flight cards or no-flights message
                        await self.page.wait_for_selector(".flt-res-card, .row.top-srh, .main-card, #row0", timeout=60000)
                        self.context.rendered_dom = await self.page.content()
                        self.state = NavigationState.RESULTS_DETECTED
                    except Exception as e:
                        logger.warning(f"EaseMyTripNavigation: Timeout waiting for results. {e}")
                        if await self._is_protection_detected():
                            self.state = NavigationState.PROTECTION_DETECTED
                        else:
                            # Let's save the DOM anyway to see what happened
                            self.context.rendered_dom = await self.page.content()
                            self.state = NavigationState.EMPTY_RESULTS
                    
                elif self.state == NavigationState.RESULTS_DETECTED:
                    self.context.terminal_state = NavigationState.RESULTS_DETECTED
                    break
                    
                elif self.state in (NavigationState.PROTECTION_DETECTED, NavigationState.CAPTCHA_DETECTED, NavigationState.EMPTY_RESULTS, NavigationState.SEARCH_ERROR, NavigationState.TIMEOUT):
                    logger.warning(f"EaseMyTripNavigation: Hit terminal failure state: {self.state}")
                    self.context.terminal_state = self.state
                    break
                    
            except Exception as e:
                logger.error(f"EaseMyTripNavigation: Error during state {self.state}: {e}")
                self.context.terminal_state = NavigationState.SEARCH_ERROR
                break
                
        return self.context
        
    async def _is_protection_detected(self) -> bool:
        """Check if CAPTCHA or Cloudflare protection is on the page."""
        text = (await self.page.locator("body").inner_text()).lower()
        markers = ["captcha", "verify you are human", "checking your browser", "security check"]
        return any(m in text for m in markers)
