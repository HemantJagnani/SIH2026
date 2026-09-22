"""
adapter.py — IndiGo source adapter (Phase 9).

The IndigoAdapter contains only IndiGo-specific logic. It is called by the
CollectionOrchestrator which owns the generic pipeline:
  PolicyGate → RateLimiter → SessionManager → crawler.run()
                                ↓
                           IndigoAdapter.search()
                                ↓
                  navigation.run_search_workflow()
                  parser.extract_from_network_response()
                    or  parser.extract_from_dom()
                  normalizer.*
                                ↓
                       list[FareObservation]

Adapter version must be bumped whenever navigation.py or parser.py changes
in a way that affects produced observations.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from models.observation import FareObservation
from models.request import FareSearchRequest
from models.enums import AvailabilityStatus, CabinClass, TripType, WorkflowState

from . import selectors, navigation, parser

logger = logging.getLogger(__name__)

ADAPTER_VERSION = "1.0.0"
SOURCE_ID = "indigo"
INDIGO_URL = "https://www.goindigo.in/"


class IndigoAdapter:
    """
    Source adapter for IndiGo (www.goindigo.in).

    Usage (called by CollectionOrchestrator):

        adapter = IndigoAdapter()
        observations, terminal_state = await adapter.search(page, request, run_id)
        # observations is [] on blocking failure
        # terminal_state is the WorkflowState for evidence recording
    """

    @property
    def adapter_version(self) -> str:
        return ADAPTER_VERSION

    @property
    def normalizer_version(self) -> str:
        from normalization.core import PIPELINE_VERSION
        return PIPELINE_VERSION

    @property
    def parser_version(self) -> str:
        return parser.PARSER_VERSION

    async def search(
        self,
        page: Any,
        request: FareSearchRequest,
        run_id: Optional[str] = None,
    ) -> tuple[list[FareObservation], WorkflowState]:
        """
        Execute the full IndiGo search workflow and return fare observations.

        This method orchestrates navigation → extraction → normalization.
        It does NOT handle: rate limiting, robots check, session save/load,
        evidence capture — those are all handled by CollectionOrchestrator.

        Args:
            page: Playwright Page object (managed by the orchestrator's crawler).
            request: The canonical search request.
            run_id: UUID string for this collection run (for linking evidence).

        Returns:
            (observations, terminal_state) where:
                observations: List of FareObservation objects (empty on failure)
                terminal_state: The WorkflowState that ended the run
        """
        run_id = run_id or str(uuid.uuid4())
        collected_at = datetime.now(timezone.utc)

        # ----------------------------------------------------------------
        # Step 1: Set up network response interception
        # We capture the first search API response to prefer JSON over DOM.
        # ----------------------------------------------------------------
        intercepted_json: Optional[dict] = None

        async def capture_response(response):
            nonlocal intercepted_json
            if intercepted_json is not None:
                return  # Already captured
            url = response.url
            if any(pattern.strip() in url for pattern in selectors.SEARCH_API_URL_PATTERN.split(",")):
                try:
                    ct = response.headers.get("content-type", "")
                    if "json" in ct:
                        intercepted_json = await response.json()
                        logger.info("IndigoAdapter: intercepted JSON from %s.", url)
                except Exception as exc:
                    logger.debug("IndigoAdapter: could not parse intercepted response — %s", exc)

        page.on("response", capture_response)

        # ----------------------------------------------------------------
        # Step 2: Run the navigation workflow
        # ----------------------------------------------------------------
        terminal_state = await navigation.run_search_workflow(page, request)

        # ----------------------------------------------------------------
        # Step 3: On blocking failure — return immediately with empty list
        # ----------------------------------------------------------------
        blocking_states = {
            WorkflowState.CAPTCHA_BLOCKED,
            WorkflowState.ACCESS_BLOCKED,
            WorkflowState.AUTH_REQUIRED,
            WorkflowState.RATE_LIMITED,
            WorkflowState.ROBOTS_DISALLOWED,
            WorkflowState.SCHEMA_CHANGED,
            WorkflowState.SEARCH_ERROR,
            WorkflowState.NO_RESULTS,
        }
        if terminal_state in blocking_states:
            logger.warning(
                "IndigoAdapter: search ended with state '%s' — no observations.",
                terminal_state.value,
            )
            return [], terminal_state

        # ----------------------------------------------------------------
        # Step 4: Extract raw fares (JSON first, DOM fallback)
        # ----------------------------------------------------------------
        if intercepted_json:
            raw_fares = await parser.extract_from_network_response(intercepted_json)
            extraction_source = "json"
        else:
            try:
                raw_fares = await parser.extract_from_dom(page)
                extraction_source = "dom"
            except parser.ParserError as exc:
                logger.error("IndigoAdapter: parser error — %s", exc)
                return [], WorkflowState.SCHEMA_CHANGED

        logger.info(
            "IndigoAdapter: extracted %d raw fares via %s.",
            len(raw_fares), extraction_source,
        )

        if not raw_fares:
            return [], WorkflowState.NO_RESULTS

        # ----------------------------------------------------------------
        # Step 5: Normalize and build FareObservation objects
        # ----------------------------------------------------------------
        observations = []
        for raw in raw_fares:
            obs = self._build_observation(raw, request, run_id, collected_at)
            if obs is not None:
                observations.append(obs)

        logger.info("IndigoAdapter: built %d valid observations.", len(observations))
        return observations, WorkflowState.DONE

    def _build_observation(
        self,
        raw: dict,
        request: FareSearchRequest,
        run_id: str,
        collected_at: datetime,
    ) -> Optional[FareObservation]:
        """
        Normalize one raw fare dict into a FareObservation.
        Returns None if the observation fails validation (logged with reason).
        """
        try:
            from normalization.prices import normalize_price
            from normalization.dates import normalize_time_local, to_utc
            from normalization.entities import normalize_flight_number
            from normalization.core import NormalizationException
            
            # Normalize price components.
            try:
                total_fare_res = normalize_price(str(raw.get("total_fare") or ""))
                total_fare = total_fare_res.normalized_value
            except NormalizationException as e:
                logger.warning(f"IndigoAdapter: rejecting fare with invalid total_fare: {e.reason}")
                return None
                
            base_fare = None
            if raw.get("base_fare"):
                try:
                    base_fare = normalize_price(str(raw.get("base_fare"))).normalized_value
                except NormalizationException:
                    pass
                    
            taxes = None
            if raw.get("taxes"):
                try:
                    taxes = normalize_price(str(raw.get("taxes"))).normalized_value
                except NormalizationException:
                    pass

            # Reject zero or missing total_fare — never invent a price.
            if total_fare is None or total_fare <= 0:
                logger.warning(
                    "IndigoAdapter: rejecting fare with invalid total_fare='%s'.",
                    raw.get("total_fare"),
                )
                return None

            # Normalize times.
            dep_local = None
            if raw.get("departure_time"):
                try:
                    dep_local = normalize_time_local(raw.get("departure_time"), request.travel_date).normalized_value
                except NormalizationException:
                    pass
                    
            arr_local = None
            if raw.get("arrival_time"):
                try:
                    arr_local = normalize_time_local(raw.get("arrival_time"), request.travel_date).normalized_value
                except NormalizationException:
                    pass
                    
            dep_utc = to_utc(dep_local) if dep_local else None
            arr_utc = to_utc(arr_local) if arr_local else None

            # Stops: parse to int if present.
            stops_raw = raw.get("stops")
            stops: Optional[int] = None
            if stops_raw is not None:
                try:
                    stops_text = str(stops_raw).strip().lower()
                    if "non-stop" in stops_text or "direct" in stops_text:
                        stops = 0
                    else:
                        stops = int(re.search(r"\d+", stops_text).group())
                except Exception:
                    stops = None
                    
            flight_num = None
            if raw.get("flight_number"):
                try:
                    flight_num = normalize_flight_number(raw.get("flight_number")).normalized_value
                except NormalizationException:
                    pass

            from validation.pipeline import validate_observation
            
            obs_data = dict(
                collection_run_id=uuid.UUID(run_id),
                source=SOURCE_ID,
                source_offer_id=raw.get("source_offer_id"),
                source_url=INDIGO_URL,
                collected_at=collected_at,
                search_timestamp=collected_at,

                travel_date=request.travel_date,
                lead_days=request.lead_days,
                origin=request.origin,
                destination=request.destination,

                airline="IndiGo",
                airline_code="6E",
                flight_number=flight_num,

                trip_type=request.trip_type,
                cabin=request.cabin,
                passenger_count=request.passenger_count.adults,

                departure_time_local=dep_local,
                departure_time_utc=dep_utc,
                arrival_time_local=arr_local,
                arrival_time_utc=arr_utc,
                stops=stops,

                fare_family=raw.get("fare_family"),
                fare_class=raw.get("fare_class"),

                base_fare=base_fare,
                taxes=taxes,
                total_fare=total_fare,
                currency="INR",

                availability=AvailabilityStatus.AVAILABLE,

                adapter_version=self.adapter_version,
                normalizer_version=self.normalizer_version,
            )
            
            obs, val_result = validate_observation(obs_data)
            if not val_result.is_valid:
                logger.warning("IndigoAdapter: observation failed validation: %s", val_result.errors)
                return None
                
            return obs

        except Exception as exc:
            logger.error("IndigoAdapter: FareObservation construction failed — %s", exc)
            return None


# Lazy import of re for stops parsing above
import re

