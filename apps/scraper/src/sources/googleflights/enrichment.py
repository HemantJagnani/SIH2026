"""
Bounded Enrichment for Google Flights (Phase 9).

States:
- SELECT_ITINERARY
- DETAIL_VIEW
- FARES_VIEW
- FARE_OPTIONS_VIEW
- BAGGAGE_VIEW
- FARE_RULES_VIEW
- ENRICHMENT_COMPLETE

Guarantees:
- Explicit timeouts per transition.
- State verification after each interaction (no blind assumptions).
- Graceful handling: records ENRICHMENT_STATE_NOT_REACHED if state not verified.
- Does not attempt CAPTCHA or anti-bot evasion.
"""

from __future__ import annotations

import asyncio
import logging
from enum import Enum
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup

from models.enrichment import EnrichmentStatus, EnrichmentTask, EnrichmentType
from sources.googleflights.selectors import GoogleFlightsSelectors
from sources.googleflights.parser import parse_expanded_cards

logger = logging.getLogger(__name__)


class GoogleEnrichmentState(str, Enum):
    SELECT_ITINERARY = "SELECT_ITINERARY"
    DETAIL_VIEW = "DETAIL_VIEW"
    FARES_VIEW = "FARES_VIEW"
    FARE_OPTIONS_VIEW = "FARE_OPTIONS_VIEW"
    BAGGAGE_VIEW = "BAGGAGE_VIEW"
    FARE_RULES_VIEW = "FARE_RULES_VIEW"
    ENRICHMENT_COMPLETE = "ENRICHMENT_COMPLETE"
    ENRICHMENT_STATE_NOT_REACHED = "ENRICHMENT_STATE_NOT_REACHED"
    BLOCKED = "BLOCKED"


class GoogleFlightsEnrichment:
    """
    Executes bounded state machine enrichment on selected Google Flights result cards.
    """

    def __init__(self, page: Any, timeout_ms: int = 4000):
        self.page = page
        self.timeout_ms = timeout_ms

    async def enrich_card(
        self,
        card_index: int,
        task: Optional[EnrichmentTask] = None,
    ) -> tuple[Optional[str], GoogleEnrichmentState, dict[str, Any]]:
        """
        Executes bounded state transitions for a single card index.
        Returns (html_content, terminal_state, diagnostics).
        """
        current_state = GoogleEnrichmentState.SELECT_ITINERARY
        diagnostics: dict[str, Any] = {
            "card_index": card_index,
            "transitions": [],
            "failure_reason": None,
        }

        try:
            # 1. State: SELECT_ITINERARY
            logger.info(f"GoogleEnrichment [Card {card_index}]: Transitioning to SELECT_ITINERARY")
            expand_buttons = self.page.locator(GoogleFlightsSelectors.EXPAND_CARD_BUTTON)
            count = await expand_buttons.count()
            if card_index >= count:
                logger.warning(f"GoogleEnrichment: card_index {card_index} out of range ({count} cards)")
                diagnostics["failure_reason"] = "CARD_INDEX_OUT_OF_RANGE"
                return None, GoogleEnrichmentState.ENRICHMENT_STATE_NOT_REACHED, diagnostics

            target_btn = expand_buttons.nth(card_index)
            if not await target_btn.is_visible():
                await target_btn.scroll_into_view_if_needed()
                await asyncio.sleep(0.3)

            # Click to expand
            await target_btn.click(timeout=self.timeout_ms)
            diagnostics["transitions"].append("CLICK_EXPAND")

            # 2. State: DETAIL_VIEW (Verify state)
            details_panel = self.page.locator(GoogleFlightsSelectors.DETAILS_PANEL).first
            try:
                await details_panel.wait_for(state="visible", timeout=self.timeout_ms)
                current_state = GoogleEnrichmentState.DETAIL_VIEW
                diagnostics["transitions"].append("DETAIL_VIEW_REACHED")
                logger.info(f"GoogleEnrichment [Card {card_index}]: DETAIL_VIEW reached and verified.")
            except Exception as e:
                logger.warning(f"GoogleEnrichment: Failed to reach DETAIL_VIEW: {e}")
                diagnostics["failure_reason"] = "DETAIL_PANEL_TIMEOUT"
                return None, GoogleEnrichmentState.ENRICHMENT_STATE_NOT_REACHED, diagnostics

            # Grab parent HTML containing flight details
            parent_li = target_btn.locator("xpath=ancestor::li").first
            expanded_html = await parent_li.inner_html()

            # 3. State: FARES_VIEW / FARE_OPTIONS_VIEW (optional inspection)
            fare_select_btn = parent_li.locator(GoogleFlightsSelectors.FARE_FAMILY_BUTTON).first
            if await fare_select_btn.count() > 0 and await fare_select_btn.is_visible():
                try:
                    logger.info(f"GoogleEnrichment [Card {card_index}]: Attempting FARES_VIEW...")
                    await fare_select_btn.click(timeout=self.timeout_ms)
                    modal = self.page.locator(GoogleFlightsSelectors.FARE_OPTIONS_MODAL).first
                    await modal.wait_for(state="visible", timeout=self.timeout_ms)
                    current_state = GoogleEnrichmentState.FARE_OPTIONS_VIEW
                    diagnostics["transitions"].append("FARE_OPTIONS_VIEW_REACHED")
                    
                    # Capture modal HTML
                    modal_html = await modal.inner_html()
                    expanded_html += f"\n<!-- FARE_OPTIONS_MODAL -->\n{modal_html}"

                    # Close modal cleanly
                    close_btn = modal.locator('button[aria-label="Close"], button:has-text("Close"), button:has-text("Back")').first
                    if await close_btn.count() > 0 and await close_btn.is_visible():
                        await close_btn.click(timeout=self.timeout_ms)
                    else:
                        await self.page.keyboard.press("Escape")
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logger.debug(f"GoogleEnrichment: FARE_OPTIONS_VIEW not reached or absent: {e}")
                    # Graceful non-blocking fallback
                    await self.page.keyboard.press("Escape")
                    await asyncio.sleep(0.3)

            # Collapse the card back to clean up view
            try:
                await target_btn.click(timeout=self.timeout_ms)
                await asyncio.sleep(0.3)
            except Exception:
                pass

            current_state = GoogleEnrichmentState.ENRICHMENT_COMPLETE
            diagnostics["transitions"].append("ENRICHMENT_COMPLETE")
            return expanded_html, current_state, diagnostics

        except Exception as exc:
            logger.error(f"GoogleEnrichment [Card {card_index}]: Error during enrichment — {exc}")
            diagnostics["failure_reason"] = str(exc)
            # Try escaping out of any open modal
            try:
                await self.page.keyboard.press("Escape")
            except Exception:
                pass
            return None, GoogleEnrichmentState.ENRICHMENT_STATE_NOT_REACHED, diagnostics
