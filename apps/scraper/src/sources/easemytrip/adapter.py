"""
Adapter for EaseMyTrip (Phase 11, 12, 13, 14, 15).

Resilient source adapter:
- Detects blocks and performs immediate safe stop.
- Never crashes the parent collection run.
- Generates machine-readable diagnostics.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple
from uuid import UUID

from models.enums import WorkflowState
from models.observation import FareObservation
from models.request import FareSearchRequest
from sources.easemytrip.navigation import EaseMyTripNavigation, NavigationState, SearchResultContext
from sources.easemytrip.parser import parse_dom, parse_network_response
from validation.pipeline import validate_observation

logger = logging.getLogger(__name__)


class EaseMyTripAdapter:
    """
    FareSourceAdapter for EaseMyTrip.
    """

    def __init__(
        self,
        include_fare_options: bool = False,
        result_stability_interval: float = 2.0,
        result_stability_required: int = 3,
        result_max_wait: float = 30.0,
    ):
        self.source_id = "easemytrip"
        self.include_fare_options = include_fare_options
        self.result_stability_interval = result_stability_interval
        self.result_stability_required = result_stability_required
        self.result_max_wait = result_max_wait
        self.last_diagnostics = None
        self.last_stabilization_telemetry = None

    async def search(
        self,
        page,
        request: FareSearchRequest,
        run_id: UUID,
    ) -> Tuple[List[FareObservation], WorkflowState]:
        """
        Execute the search sequence for EaseMyTrip.
        Guarantees isolation: an EaseMyTrip block safely halts this source without crashing the run.
        """
        logger.info(
            f"EaseMyTripAdapter: Starting search for {request.origin}->{request.destination} "
            f"on {request.travel_date}"
        )

        nav = EaseMyTripNavigation(
            page,
            request,
            result_stability_interval=self.result_stability_interval,
            result_stability_required=self.result_stability_required,
            result_max_wait=self.result_max_wait,
        )
        context: SearchResultContext = await nav.execute()
        self.last_diagnostics = context.diagnostics
        self.last_stabilization_telemetry = {
            "initial_cards": context.initial_cards,
            "final_cards": context.final_cards,
            "cards_added_during_stabilization": context.cards_added_during_stabilization,
            "stabilization_duration": context.stabilization_duration,
            "stabilization_history": context.stabilization_history,
        }

        term_state = context.terminal_state
        workflow_state = WorkflowState.SEARCH_ERROR

        if term_state == NavigationState.RESULTS_DETECTED:
            workflow_state = WorkflowState.DONE
        elif term_state == NavigationState.CAPTCHA_DETECTED:
            workflow_state = WorkflowState.CAPTCHA_BLOCKED
        elif term_state == NavigationState.PROTECTION_DETECTED:
            workflow_state = WorkflowState.ACCESS_BLOCKED
        elif term_state == NavigationState.ACCESS_BLOCKED:
            workflow_state = WorkflowState.ACCESS_BLOCKED
        elif term_state == NavigationState.EMPTY_RESULTS:
            workflow_state = WorkflowState.NO_RESULTS
        elif term_state == NavigationState.TIMEOUT:
            workflow_state = WorkflowState.SEARCH_ERROR

        # Safe stop handling (Phase 12)
        if term_state != NavigationState.RESULTS_DETECTED:
            diag_reason = (
                context.diagnostics.failure_classification.value
                if context.diagnostics
                else "UNKNOWN"
            )
            logger.warning(
                f"EaseMyTripAdapter: Source halted at state '{term_state.value}'. "
                f"Diagnostic classification: {diag_reason}. Stopping safely."
            )
            return [], workflow_state

        # Parse results from DOM
        observations: List[FareObservation] = []
        if context.rendered_dom:
            raw_observations = parse_dom(
                html=context.rendered_dom,
                request=request,
                run_id=run_id,
                source_id=self.source_id,
                include_fare_options=self.include_fare_options,
                source_url=page.url if hasattr(page, "url") else None,
            )

            # Validate observations
            for obs in raw_observations:
                validated_fare, validation_result = validate_observation(obs.model_dump(mode="json"))
                if validation_result.is_valid and validated_fare:
                    observations.append(validated_fare)
                else:
                    logger.debug("EaseMyTripAdapter: Observation rejected during validation.")
        else:
            logger.error("EaseMyTripAdapter: No parseable DOM despite RESULTS_DETECTED.")
            return [], WorkflowState.SEARCH_ERROR

        logger.info(f"EaseMyTripAdapter: Extracted {len(observations)} valid observations.")
        return observations, workflow_state
