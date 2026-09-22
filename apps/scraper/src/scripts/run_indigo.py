"""
run_indigo.py — CLI runner for IndiGo browser collection (Phase 9, Milestone 4).

Usage:
    python -m apps.scraper.src.scripts.run_indigo [OPTIONS]

    python apps/scraper/src/scripts/run_indigo.py --headless
    python apps/scraper/src/scripts/run_indigo.py --date 2026-10-10 --headless

Environment:
    PYTHONPATH=apps/scraper/src

This script exercises the full pipeline:
  CollectionOrchestrator → IndigoAdapter → navigation → parser → normalizer

Path A (accessible result): observations are printed and stored.
Path B (protection detected): blocking state is printed, evidence dir logged.

Test parameters (per implementation plan):
  Route: DEL → BOM
  Date: T+7 (default)
  Passengers: 1 adult
  Cabin: ECONOMY
  Trip: ONE_WAY
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import date, timedelta
from pathlib import Path

# Make scraper src importable.
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.request import FareSearchRequest, PassengerCount
from models.enums import CabinClass, CollectionMode, TripType, WorkflowState
from core.orchestrator import CollectionOrchestrator
from core.rate_limiter import SourceRateLimitConfig
from sources.airlines.indigo.adapter import IndigoAdapter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("run_indigo")

INDIGO_URL = "https://www.goindigo.in/"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="IndiGo fare collection — Phase 9 M4")
    parser.add_argument(
        "--origin", default="DEL",
        help="Departure IATA code (default: DEL)"
    )
    parser.add_argument(
        "--destination", default="BOM",
        help="Arrival IATA code (default: BOM)"
    )
    parser.add_argument(
        "--date", default=None,
        help="Travel date YYYY-MM-DD (default: today + 7 days)"
    )
    parser.add_argument(
        "--headless", action="store_true",
        help="Run browser in headless mode (default: False — shows browser)"
    )
    parser.add_argument(
        "--ignore-robots", action="store_true",
        help="Bypass robots.txt for testing the browser workflow"
    )
    return parser.parse_args()


class DummyPolicyGate:
    """A bypass for testing the scraper workflow when robots.txt blocks."""
    async def check(self, url: str) -> tuple[bool, str]:
        return True, "Robots.txt check bypassed via CLI flag"


async def main():
    args = parse_args()

    # Resolve travel date.
    if args.date:
        try:
            travel_date = date.fromisoformat(args.date)
        except ValueError:
            logger.error("Invalid date format '%s'. Use YYYY-MM-DD.", args.date)
            sys.exit(1)
    else:
        travel_date = date.today() + timedelta(days=7)

    lead_days = (travel_date - date.today()).days
    if lead_days < 0:
        logger.error("Travel date %s is in the past.", travel_date)
        sys.exit(1)

    # Build the canonical search request.
    request = FareSearchRequest(
        source="indigo",
        origin=args.origin,
        destination=args.destination,
        travel_date=travel_date,
        lead_days=lead_days,
        trip_type=TripType.ONE_WAY,
        cabin=CabinClass.ECONOMY,
        passenger_count=PassengerCount(adults=1),
        collection_mode=CollectionMode.BROWSER,
    )

    logger.info("=" * 60)
    logger.info("IndiGo Collection — Phase 9 Milestone 4")
    logger.info("Route: %s → %s", request.origin, request.destination)
    logger.info("Date:  %s (T+%d)", travel_date, lead_days)
    logger.info("Mode:  %s", "headless" if args.headless else "visible browser")
    logger.info("=" * 60)

    policy_gate = DummyPolicyGate() if args.ignore_robots else None

    # Build the orchestrator with IndiGo-specific config.
    orchestrator = CollectionOrchestrator(
        source_id="indigo",
        source_url=INDIGO_URL,
        adapter=IndigoAdapter(),
        # Conservative rate limit per sources.yaml.
        rate_limit_config=SourceRateLimitConfig(min_interval_seconds=5.0),
        policy_gate=policy_gate,
        headless=args.headless,
    )

    # Run the collection.
    result = await orchestrator.run(request)

    logger.info("=" * 60)
    logger.info("Run ID:         %s", result.run_id)
    logger.info("Terminal state: %s", result.terminal_state.value)
    if result.evidence_dir:
        logger.info("Evidence dir:   %s", result.evidence_dir)
    logger.info("=" * 60)

    # ----------------------------------------------------------------
    # Path A: Successful extraction
    # ----------------------------------------------------------------
    if result.terminal_state == WorkflowState.DONE:
        logger.info("✅ PATH A — Fare extraction SUCCESSFUL")
        logger.info("   Observations: %d", len(result.observations))
        for i, obs in enumerate(result.observations[:5], 1):
            logger.info(
                "   [%d] %s | dep=%s | arr=%s | fare=₹%s | cabin=%s",
                i,
                obs.flight_number or "N/A",
                obs.departure_time_local.strftime("%H:%M") if obs.departure_time_local else "?",
                obs.arrival_time_local.strftime("%H:%M") if obs.arrival_time_local else "?",
                obs.total_fare,
                obs.cabin.value,
            )
        if len(result.observations) > 5:
            logger.info("   ... and %d more.", len(result.observations) - 5)

    # ----------------------------------------------------------------
    # Path B: Source protected / blocked
    # ----------------------------------------------------------------
    elif result.was_blocked:
        logger.warning("🚫 PATH B — Source protection detected")
        logger.warning("   Status:  %s", result.terminal_state.value)
        logger.warning(
            "   Action:  Evidence captured. No retry. No session rotation. Source paused for this run."
        )

    # ----------------------------------------------------------------
    # Other failure states
    # ----------------------------------------------------------------
    else:
        logger.warning("⚠️  %s — %d observations.", result.terminal_state.value, len(result.observations))

    return result


if __name__ == "__main__":
    asyncio.run(main())
