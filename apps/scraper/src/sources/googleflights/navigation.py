import asyncio
import logging
import time
from enum import Enum
from typing import Optional

from sources.googleflights.url_builder import GoogleFlightsUrlBuilder
from sources.googleflights.selectors import GoogleFlightsSelectors

logger = logging.getLogger(__name__)

class NavigationState(Enum):
    INIT = "INIT"
    CONSENT_REQUIRED = "CONSENT_REQUIRED"
    SEARCH_SUBMITTED = "SEARCH_SUBMITTED"
    RESULTS_LOADING = "RESULTS_LOADING"
    RESULTS_DETECTED = "RESULTS_DETECTED"
    NO_RESULTS = "NO_RESULTS"
    CAPTCHA_DETECTED = "CAPTCHA_DETECTED"
    ACCESS_BLOCKED = "ACCESS_BLOCKED"
    SERVER_ERROR = "SERVER_ERROR"
    TIMEOUT = "TIMEOUT"
    PARSE_READY = "PARSE_READY"
    FAILED = "FAILED"

class SearchResultContext:
    def __init__(self):
        self.terminal_state: Optional[NavigationState] = None
        self.rendered_dom: Optional[str] = None
        self.evidence: dict = {}

class GoogleFlightsNavigation:
    def __init__(self, page, request):
        self.page = page
        self.request = request
        self.context = SearchResultContext()
        self.state = NavigationState.INIT
        
    async def execute(self) -> SearchResultContext:
        """Run the state machine for Google Flights navigation."""
        while True:
            try:
                if self.state == NavigationState.INIT:
                    url = GoogleFlightsUrlBuilder.build_url(self.request)
                    logger.info(f"GoogleFlightsNavigation: Navigating to {url}")
                    await self.page.goto(url)
                    self.state = NavigationState.CONSENT_REQUIRED
                
                elif self.state == NavigationState.CONSENT_REQUIRED:
                    # Check for consent or directly move to search loading
                    logger.info("GoogleFlightsNavigation: Checking for GDPR consent form...")
                    try:
                        # Wait briefly for consent button
                        accept_btn = self.page.locator(GoogleFlightsSelectors.CONSENT_ACCEPT_BUTTON).first
                        if await accept_btn.is_visible(timeout=3000):
                            logger.info("GoogleFlightsNavigation: Consent button found. Clicking it.")
                            await accept_btn.click()
                            await asyncio.sleep(1) # Give it a moment to vanish
                    except Exception:
                        pass # No consent form, which is fine
                    
                    self.state = NavigationState.RESULTS_LOADING
                    
                elif self.state == NavigationState.RESULTS_LOADING:
                    logger.info("GoogleFlightsNavigation: Waiting for results to load and stabilize...")
                    
                    if await self._is_protection_detected():
                        self.state = NavigationState.ACCESS_BLOCKED
                        continue
                    
                    try:
                        # Wait for the main results container
                        await self.page.wait_for_selector(GoogleFlightsSelectors.RESULTS_CONTAINER, timeout=28000)
                        
                        # Wait for stabilization (scroll down briefly to load lazy elements)
                        await self.page.mouse.wheel(0, 1000)
                        await asyncio.sleep(2)
                        await self.page.mouse.wheel(0, 1000)
                        await asyncio.sleep(2)
                        
                        # Check if no results indicator is present
                        no_res = self.page.locator(GoogleFlightsSelectors.NO_RESULTS_INDICATOR)
                        if await no_res.count() > 0 and await no_res.first.is_visible():
                            self.state = NavigationState.NO_RESULTS
                        else:
                            self.state = NavigationState.RESULTS_DETECTED
                            
                    except Exception as e:
                        logger.warning(f"GoogleFlightsNavigation: Timeout or error waiting for results. {e}")
                        if await self._is_protection_detected():
                            self.state = NavigationState.ACCESS_BLOCKED
                        else:
                            self.state = NavigationState.TIMEOUT
                    
                elif self.state == NavigationState.RESULTS_DETECTED:
                    self.context.rendered_dom = await self.page.content()
                    self.state = NavigationState.PARSE_READY
                    
                elif self.state == NavigationState.PARSE_READY:
                    self.context.terminal_state = NavigationState.PARSE_READY
                    break
                    
                elif self.state in (
                    NavigationState.ACCESS_BLOCKED, NavigationState.CAPTCHA_DETECTED, 
                    NavigationState.NO_RESULTS, NavigationState.SERVER_ERROR, 
                    NavigationState.TIMEOUT, NavigationState.FAILED
                ):
                    logger.warning(f"GoogleFlightsNavigation: Hit terminal failure state: {self.state}")
                    self.context.terminal_state = self.state
                    # Grab DOM anyway for debugging
                    try:
                        self.context.rendered_dom = await self.page.content()
                    except:
                        pass
                    break
                    
            except Exception as e:
                logger.error(f"GoogleFlightsNavigation: Error during state {self.state}: {e}")
                self.context.terminal_state = NavigationState.FAILED
                break
                
        return self.context
        
    async def _is_protection_detected(self) -> bool:
        """Check if CAPTCHA or Google bot protection is on the page."""
        try:
            # Check specific selectors
            captcha_forms = self.page.locator(GoogleFlightsSelectors.CAPTCHA_INDICATOR)
            if await captcha_forms.count() > 0:
                return True
                
            text = (await self.page.locator("body").inner_text()).lower()
            markers = ["unusual traffic from your computer network", "captcha", "security check"]
            return any(m in text for m in markers)
        except Exception:
            return False
