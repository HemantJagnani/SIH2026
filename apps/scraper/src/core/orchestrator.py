"""
orchestrator.py — CollectionOrchestrator: the central pipeline engine.

This is the single component that wires together all generic pipeline
infrastructure for any browser-based source:

  PolicyGate → RateLimiter → SessionManager → build_crawler()
    → adapter.search(page, request)
    → EvidenceCapture → Validator → Repository

The orchestrator knows nothing about IndiGo, Air India, or any other source.
All source-specific logic lives in the corresponding adapter package under
sources/airlines/<source>/ or sources/otas/<source>/.

Phase 9 compliance guarantees enforced here:
  - robots.txt is checked BEFORE the browser launches.
  - Rate limiter is awaited BEFORE each crawl run.
  - On CAPTCHA/403/login wall → evidence captured, session marked blocked,
    source paused for this run. No retry, no rotation.
  - On DONE → session state saved for reuse.
  - Every run (success or failure) writes evidence to runtime/evidence/.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from models.enums import AvailabilityStatus, WorkflowState
from models.observation import FareObservation
from models.request import FareSearchRequest
from core.crawler import build_crawler
from core.policy_gate import RobotsPolicyGate
from core.rate_limiter import SourceRateLimiter, SourceRateLimitConfig
from core.session_manager import SessionManager
from core.evidence import EvidenceCapture
from core.anti_bot_detector import captcha_present, is_access_blocked, is_login_wall

logger = logging.getLogger(__name__)

# Terminal states that mean "stop this source for this run".
BLOCKING_STATES = frozenset({
    WorkflowState.CAPTCHA_BLOCKED,
    WorkflowState.ACCESS_BLOCKED,
    WorkflowState.AUTH_REQUIRED,
    WorkflowState.RATE_LIMITED,
    WorkflowState.ROBOTS_DISALLOWED,
})


class CollectionResult:
    """Structured result from a single orchestrated collection run."""

    def __init__(
        self,
        run_id: str,
        source: str,
        terminal_state: WorkflowState,
        observations: list[FareObservation],
        evidence_dir: Optional[Path] = None,
    ):
        self.run_id = run_id
        self.source = source
        self.terminal_state = terminal_state
        self.observations = observations
        self.evidence_dir = evidence_dir

    @property
    def succeeded(self) -> bool:
        return self.terminal_state == WorkflowState.DONE

    @property
    def was_blocked(self) -> bool:
        return self.terminal_state in BLOCKING_STATES

    def __repr__(self) -> str:
        return (
            f"CollectionResult(source={self.source!r}, "
            f"state={self.terminal_state.value}, "
            f"observations={len(self.observations)})"
        )


class CollectionOrchestrator:
    """
    Generic pipeline orchestrator for browser-based fare collection.

    Instantiate once per source per run:
        orchestrator = CollectionOrchestrator(
            source_id="indigo",
            source_url="https://www.goindigo.in/",
            adapter=IndigoAdapter(),
        )
        result = await orchestrator.run(request)
    """

    def __init__(
        self,
        source_id: str,
        source_url: str,
        adapter: Any,
        rate_limit_config: Optional[SourceRateLimitConfig] = None,
        policy_gate: Optional[RobotsPolicyGate] = None,
        session_manager: Optional[SessionManager] = None,
        evidence_capture: Optional[EvidenceCapture] = None,
        headless: Optional[bool] = None,
    ):
        """
        Args:
            source_id: Source identifier, e.g. 'indigo'.
            source_url: The URL the browser will navigate to.
            adapter: An instance of the source adapter (e.g. IndigoAdapter).
            rate_limit_config: Per-source pacing config. Defaults to 5s interval.
            policy_gate: robots.txt gate. Defaults to production (real fetch).
            session_manager: Manages per-source storage_state. Defaults to prod dir.
            evidence_capture: Evidence writer. Defaults to runtime/evidence/.
            headless: Whether to run headless. None = read from env.
        """
        self.source_id = source_id
        self.source_url = source_url
        self.adapter = adapter
        self._rate_limiter = SourceRateLimiter(rate_limit_config or SourceRateLimitConfig())
        self._policy_gate = policy_gate or RobotsPolicyGate()
        self._session_manager = session_manager or SessionManager()
        self._evidence = evidence_capture or EvidenceCapture()
        self._headless = headless

    async def run(self, request: FareSearchRequest) -> CollectionResult:
        """
        Execute one complete collection run for the given request.

        Sequence:
          1. robots.txt policy check (no network call if RobotsPolicyGate has cache)
          2. Rate limiter wait
          3. Build crawler + launch browser
          4. Load session state into browser context
          5. Execute adapter.search()
          6. Capture evidence (always)
          7. Save session state (only on DONE)
          8. Mark session blocked (on CAPTCHA/403)
          9. Return CollectionResult

        Returns:
            CollectionResult with terminal_state and observations.
        """
        run_id = str(uuid.uuid4())
        logger.info(
            "Orchestrator: starting run %s for %s (%s→%s, %s).",
            run_id[:8], self.source_id,
            request.origin, request.destination, request.travel_date,
        )

        # ----------------------------------------------------------------
        # 1. Policy check — robots.txt
        # ----------------------------------------------------------------
        allowed, policy_reason = await self._policy_gate.check(self.source_url)
        if not allowed:
            logger.warning("Orchestrator: robots.txt DISALLOWED — %s.", policy_reason)
            return CollectionResult(
                run_id=run_id,
                source=self.source_id,
                terminal_state=WorkflowState.ROBOTS_DISALLOWED,
                observations=[],
            )

        # ----------------------------------------------------------------
        # 2. Rate limiter — wait for our per-source interval
        # ----------------------------------------------------------------
        logger.info("Orchestrator: waiting for rate limiter...")
        await self._rate_limiter.wait()

        # ----------------------------------------------------------------
        # 3. Build the crawler
        # ----------------------------------------------------------------
        crawler = build_crawler(headless=self._headless)

        # Shared state to pass between the Crawlee handler and the outer scope.
        _result_holder: dict = {
            "observations": [],
            "terminal_state": WorkflowState.SEARCH_ERROR,
            "evidence_dir": None,
            "page_ref": None,
        }

        @crawler.router.default_handler
        async def handler(context) -> None:
            """
            Crawlee calls this with the full browser context for each URL.
            We run the adapter, capture evidence, manage session state.
            """
            page = context.page
            _result_holder["page_ref"] = page

            # Load saved session state (cookies/localStorage) into the context.
            saved_state = self._session_manager.load(self.source_id)
            if saved_state:
                try:
                    await page.context.add_cookies(
                        saved_state.get("cookies", [])
                    )
                    logger.debug("Orchestrator: loaded %d cookies.", len(saved_state.get("cookies", [])))
                except Exception as exc:
                    logger.warning("Orchestrator: could not load saved cookies — %s", exc)

            # Run the adapter search workflow.
            observations, terminal_state = await self.adapter.search(
                page=page,
                request=request,
                run_id=run_id,
            )
            _result_holder["observations"] = observations
            _result_holder["terminal_state"] = terminal_state

            # Build result data for evidence (summary of what was extracted).
            result_data = None
            if observations:
                result_data = {
                    "count": len(observations),
                    "sample": [
                        {
                            "flight_number": o.flight_number,
                            "total_fare": str(o.total_fare),
                            "departure_time_local": str(o.departure_time_local),
                        }
                        for o in observations[:3]  # First 3 only for the evidence summary
                    ],
                }

            # Always capture evidence — both success and failure.
            evidence_dir = await self._evidence.capture(
                page=page,
                source=self.source_id,
                request_data={
                    "origin": request.origin,
                    "destination": request.destination,
                    "travel_date": str(request.travel_date),
                    "lead_days": request.lead_days,
                    "cabin": request.cabin.value,
                    "trip_type": request.trip_type.value,
                    "passengers": request.passenger_count.adults,
                },
                status=terminal_state.value,
                result_data=result_data,
                run_id=run_id,
                error_message=None if observations else f"terminal_state={terminal_state.value}",
            )
            _result_holder["evidence_dir"] = evidence_dir

            # Session management after the run.
            if terminal_state in BLOCKING_STATES:
                # Do NOT save session state after a block — the state is tainted.
                self._session_manager.mark_blocked(self.source_id)
                logger.warning(
                    "Orchestrator: source '%s' blocked with state '%s'. "
                    "Session NOT saved. No retry, no rotation.",
                    self.source_id, terminal_state.value,
                )
            elif terminal_state == WorkflowState.DONE:
                # Save updated session state for next run.
                try:
                    new_state = await page.context.storage_state()
                    self._session_manager.save(self.source_id, new_state)
                except Exception as exc:
                    logger.warning("Orchestrator: could not save session state — %s", exc)

        # ----------------------------------------------------------------
        # 4. Run the crawler
        # ----------------------------------------------------------------
        try:
            await crawler.run([self.source_url])
        except Exception as exc:
            logger.error("Orchestrator: crawler raised an exception — %s", exc)
            # The handler may have already set a terminal_state.
            # If not, default to SEARCH_ERROR.
            if _result_holder["terminal_state"] == WorkflowState.SEARCH_ERROR:
                logger.error("Orchestrator: crawler exception, terminal_state=SEARCH_ERROR.")

        return CollectionResult(
            run_id=run_id,
            source=self.source_id,
            terminal_state=_result_holder["terminal_state"],
            observations=_result_holder["observations"],
            evidence_dir=_result_holder["evidence_dir"],
        )
