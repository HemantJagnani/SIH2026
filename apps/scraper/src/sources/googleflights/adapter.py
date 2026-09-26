"""
Adapter for Google Flights.
Implements Core Scan, Bounded Enrichment, and Multi-Stage Pipeline.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple
from uuid import UUID

from models.enums import WorkflowState
from models.observation import FareObservation
from models.provenance import ExtractionMode
from models.enrichment import EnrichmentPolicy, EnrichmentTask, EnrichmentType
from models.request import FareSearchRequest
from sources.googleflights.enrichment import GoogleFlightsEnrichment, GoogleEnrichmentState
from sources.googleflights.navigation import GoogleFlightsNavigation, NavigationState, SearchResultContext
from sources.googleflights.parser import parse_dom, parse_expanded_cards
from validation.pipeline import validate_observation

logger = logging.getLogger(__name__)


class GoogleFlightsAdapter:
    """
    FareSourceAdapter for Google Flights.
    """

    def __init__(self, extraction_mode: ExtractionMode = ExtractionMode.CORE_ONLY):
        self.source_id = "google_flights"
        self.extraction_mode = extraction_mode
        self.enrichment_policy = EnrichmentPolicy(max_samples_per_search=3, max_per_airline=2)

    async def search(
        self,
        page,
        request: FareSearchRequest,
        run_id: UUID,
        extraction_mode: Optional[ExtractionMode] = None,
    ) -> Tuple[List[FareObservation], WorkflowState]:
        """
        Execute the search sequence for Google Flights.
        1. Core scan first
        2. Quality validation
        3. Selected bounded enrichment (if mode is CORE_AND_DETAILS or FULL_AUDIT)
        """
        mode = extraction_mode or self.extraction_mode
        logger.info(
            f"GoogleFlightsAdapter: Starting search [{mode.value}] for "
            f"{request.origin}->{request.destination} on {request.travel_date}"
        )

        nav = GoogleFlightsNavigation(page, request)
        context: SearchResultContext = await nav.execute()

        term_state = context.terminal_state
        workflow_state = WorkflowState.SEARCH_ERROR
        if term_state == NavigationState.PARSE_READY:
            workflow_state = WorkflowState.DONE
        elif term_state == NavigationState.CAPTCHA_DETECTED:
            workflow_state = WorkflowState.CAPTCHA_BLOCKED
        elif term_state == NavigationState.ACCESS_BLOCKED:
            workflow_state = WorkflowState.ACCESS_BLOCKED
        elif term_state == NavigationState.NO_RESULTS:
            workflow_state = WorkflowState.NO_RESULTS

        if term_state != NavigationState.PARSE_READY:
            logger.warning(f"GoogleFlightsAdapter: search ended with state '{term_state.name}' — no observations.")
            return [], workflow_state

        if not context.rendered_dom:
            logger.error("GoogleFlightsAdapter: No parseable context available despite PARSE_READY state.")
            return [], WorkflowState.SEARCH_ERROR

        # -------------------------------------------------------------
        # STEP 1: Core Scan
        # -------------------------------------------------------------
        logger.info("GoogleFlightsAdapter: Running CORE SCAN on rendered DOM...")
        core_raw_fares = parse_dom(
            html_content=context.rendered_dom,
            request=request,
            run_id=run_id,
            source_id=self.source_id,
            source_url=page.url if hasattr(page, "url") else None,
        )

        observations: List[FareObservation] = []
        for fare_dict in core_raw_fares:
            validated_fare, validation_result = validate_observation(fare_dict)
            if validation_result.is_valid and validated_fare:
                observations.append(validated_fare)
            else:
                logger.debug("GoogleFlightsAdapter: Fare rejected during validation.")

        logger.info(f"GoogleFlightsAdapter: Core scan produced {len(observations)} valid observations.")

        # -------------------------------------------------------------
        # STEP 2: Enrichment Queue & Sample Selection (if requested)
        # -------------------------------------------------------------
        if mode in (ExtractionMode.CORE_AND_DETAILS, ExtractionMode.FULL_AUDIT) and observations:
            logger.info(f"GoogleFlightsAdapter: Performing bounded enrichment ({mode.value})...")
            enricher = GoogleFlightsEnrichment(page)

            # Sample selection based on policy (stratified, max 3)
            sampled_obs = self.enrichment_policy.select_sample(observations)
            logger.info(f"GoogleFlightsAdapter: Selected {len(sampled_obs)} observations for enrichment.")

            # Enrich each selected observation (bounded by card index)
            for idx, obs in enumerate(sampled_obs):
                try:
                    expanded_html, state, diag = await enricher.enrich_card(card_index=idx)
                    if expanded_html and state == GoogleEnrichmentState.ENRICHMENT_COMPLETE:
                        enriched_fares = parse_expanded_cards(
                            htmls=[expanded_html],
                            request=request,
                            run_id=run_id,
                            source_id=self.source_id,
                            source_url=page.url if hasattr(page, "url") else None,
                        )
                        if enriched_fares:
                            ef = enriched_fares[0]
                            # Update observation with enriched details
                            if ef.get("flight_segments"):
                                obs.flight_segments = ef["flight_segments"]
                            if ef.get("cabin_baggage_kg") is not None:
                                obs.cabin_baggage_kg = ef["cabin_baggage_kg"]
                            if ef.get("checkin_baggage_kg") is not None:
                                obs.checkin_baggage_kg = ef["checkin_baggage_kg"]
                            if ef.get("flight_number") and not obs.flight_number:
                                obs.flight_number = ef["flight_number"]
                            # Merge provenance
                            if ef.get("field_provenance"):
                                obs.field_provenance.update(ef["field_provenance"])
                except Exception as e:
                    logger.warning(f"GoogleFlightsAdapter: Enrichment error for item {idx}: {e}")

        logger.info(f"GoogleFlightsAdapter: Finished with {len(observations)} total observations.")
        return observations, workflow_state
