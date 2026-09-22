"""
Adapter for EaseMyTrip.
"""
import logging
from typing import Optional, Tuple, List
from uuid import UUID

from models.request import FareSearchRequest
from models.observation import FareObservation
from models.enums import WorkflowState
from sources.easemytrip.navigation import EaseMyTripNavigation, NavigationState, SearchResultContext
from sources.easemytrip.parser import parse_network_response, parse_dom
from validation.pipeline import validate_observation

logger = logging.getLogger(__name__)

class EaseMyTripAdapter:
    """
    FareSourceAdapter for EaseMyTrip.
    """
    def __init__(self):
        self.source_id = "easemytrip"

    async def search(self, page, request: FareSearchRequest, run_id: UUID) -> Tuple[List[FareObservation], WorkflowState]:
        """
        Execute the search sequence for EaseMyTrip.
        """
        logger.info(f"EaseMyTripAdapter: Starting search for {request.origin}->{request.destination} on {request.travel_date}")
        
        nav = EaseMyTripNavigation(page, request)
        context: SearchResultContext = await nav.execute()

        term_state = context.terminal_state
        workflow_state = WorkflowState.SEARCH_ERROR
        if term_state == NavigationState.RESULTS_DETECTED:
            workflow_state = WorkflowState.DONE
        elif term_state == NavigationState.CAPTCHA_DETECTED:
            workflow_state = WorkflowState.CAPTCHA_BLOCKED
        elif term_state == NavigationState.PROTECTION_DETECTED:
            workflow_state = WorkflowState.ACCESS_BLOCKED
        elif term_state == NavigationState.EMPTY_RESULTS:
            workflow_state = WorkflowState.NO_RESULTS

        if term_state != NavigationState.RESULTS_DETECTED:
            logger.warning(f"EaseMyTripAdapter: search ended with state '{term_state.name}' — no observations.")
            return [], workflow_state

        # Parse results
        observations = []
        if context.network_response:
            logger.info("EaseMyTripAdapter: Found structured network response, using network parser.")
            raw_fares = parse_network_response(context.network_response, request, run_id, self.source_id)
        elif context.rendered_dom:
            logger.info("EaseMyTripAdapter: No network response found, falling back to DOM parser.")
            raw_fares = parse_dom(context.rendered_dom, request, run_id, self.source_id)
        else:
            logger.error("EaseMyTripAdapter: No parseable context available despite RESULTS_DETECTED state.")
            return [], WorkflowState.SEARCH_ERROR

        # Validate and build final observations
        for fare in raw_fares:
            validated_fare, validation_result = validate_observation(fare)
            if validation_result.is_valid and validated_fare:
                observations.append(validated_fare)
            else:
                logger.debug(f"EaseMyTripAdapter: Fare rejected during validation.")

        logger.info(f"EaseMyTripAdapter: Successfully extracted {len(observations)} valid observations.")
        return observations, workflow_state
