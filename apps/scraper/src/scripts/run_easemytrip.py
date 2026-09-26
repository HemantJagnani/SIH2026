import argparse
import asyncio
import logging
import sys
from datetime import date, timedelta
from uuid import uuid4

from core.crawler import build_crawler
from core.orchestrator import CollectionOrchestrator
from core.policy_gate import RobotsPolicyGate
from models.request import FareSearchRequest
from sources.easemytrip.adapter import EaseMyTripAdapter

def setup_logging(log_level: str):
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    )

async def main():
    parser = argparse.ArgumentParser(description="Run EaseMyTrip Fare Collector")
    parser.add_argument("--origin", type=str, required=True, help="Origin IATA code (e.g. DEL)")
    parser.add_argument("--destination", type=str, required=True, help="Destination IATA code (e.g. BOM)")
    parser.add_argument("--travel-date", type=str, required=True, help="Travel date YYYY-MM-DD")
    parser.add_argument("--lead-days", type=int, required=True, help="Days in advance")
    
    # Diagnostic options
    parser.add_argument("--headed", action="store_true", help="Run in visible browser mode")
    parser.add_argument("--save-evidence", action="store_true", help="Save evidence locally")
    parser.add_argument("--log-level", type=str, default="INFO", help="Logging level (DEBUG, INFO, etc)")
    parser.add_argument("--dry-run", action="store_true", help="Do not persist to database")

    args = parser.parse_args()
    setup_logging(args.log_level)
    
    logger = logging.getLogger("run_easemytrip")
    logger.info("=" * 60)
    logger.info("EaseMyTrip Collection — Phase 9 Milestone 6")
    logger.info(f"Route: {args.origin} → {args.destination}")
    logger.info(f"Date:  {args.travel_date} (T+{args.lead_days})")
    logger.info(f"Mode:  {'visible browser' if args.headed else 'headless'}")
    logger.info("=" * 60)

    # Note: --ignore-robots is explicitly NOT exposed per project rules.
    policy_gate = RobotsPolicyGate()
    adapter = EaseMyTripAdapter()
    
    logger.info("run_easemytrip: Starting orchestrator...")
    orchestrator = CollectionOrchestrator(
        source_id="easemytrip",
        source_url="https://www.easemytrip.com",
        adapter=adapter,
        policy_gate=policy_gate,
        headless=not args.headed
    )

    request = FareSearchRequest(
        source="easemytrip",
        collection_mode="BROWSER",
        origin=args.origin,
        destination=args.destination,
        travel_date=date.fromisoformat(args.travel_date),
        lead_days=args.lead_days,
        passenger_count={"adults": 1, "children": 0, "infants": 0},
        cabin="ECONOMY",
        trip_type="ONE_WAY",
        market="IN"
    )

    run_id = uuid4()
    result = await orchestrator.run(request)
    observations = result.observations
    
    logger.info("=" * 60)
    logger.info(f"Run ID:         {run_id}")
    logger.info(f"Observations:   {len(observations)}")
    logger.info("=" * 60)
    
    if not args.dry_run and observations:
        logger.info("Saving to database... (Mocked for now)")
        # DB logic goes here

if __name__ == "__main__":
    asyncio.run(main())
