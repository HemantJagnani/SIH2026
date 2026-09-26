import asyncio
import logging
import argparse
from datetime import datetime, date, timedelta
import json
from pathlib import Path
from uuid import uuid4

from core.orchestrator import CollectionOrchestrator
from core.policy_gate import RobotsPolicyGate
from models.request import FareSearchRequest
from sources.googleflights.adapter import GoogleFlightsAdapter

def setup_logging(log_level: str):
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    )

async def main():
    parser = argparse.ArgumentParser(description="Run Full Audit Collection for Google Flights (Phase D)")
    parser.add_argument("--source", type=str, default="google_flights", help="Source to audit")
    parser.add_argument("--headed", action="store_true", help="Run in visible browser mode")
    parser.add_argument("--log-level", type=str, default="INFO", help="Logging level")
    
    args = parser.parse_args()
    setup_logging(args.log_level)
    logger = logging.getLogger("run_audit")
    
    from sources.easemytrip.adapter import EaseMyTripAdapter
    
    if args.source == "google_flights":
        adapter = GoogleFlightsAdapter()
        source_url = "https://www.google.com/travel/flights"
    elif args.source == "easemytrip":
        adapter = EaseMyTripAdapter()
        source_url = "https://www.easemytrip.com"
    else:
        logger.error(f"Unknown source {args.source}")
        return
        
    policy_gate = RobotsPolicyGate()

    orchestrator = CollectionOrchestrator(
        source_id=args.source,
        source_url=source_url,
        adapter=adapter,
        policy_gate=policy_gate,
        headless=not args.headed
    )

    travel_date = date.today() + timedelta(days=7)
    request = FareSearchRequest(
        source=args.source,
        origin="DEL",
        destination="BOM",
        travel_date=travel_date,
        lead_days=7,
        trip_type="ONE_WAY",
        cabin="ECONOMY",
        adults=1,
        children=0,
        infants=0,
        currency="INR",
        collection_mode="BROWSER"
    )

    logger.info("=" * 60)
    logger.info(f"Starting Full Audit Collection for {args.source} on DEL-BOM T+7 ({travel_date})")
    logger.info("=" * 60)

    try:
        result = await orchestrator.run(request)
        
        valid_obs = len(result.observations)
        logger.info(f"Successfully collected {valid_obs} observations.")
        
        # Calculate coverage
        coverage = {
            "total_observations": valid_obs,
            "fields_populated": {
                "cabin_baggage_kg": sum(1 for o in result.observations if o.cabin_baggage_kg is not None),
                "checkin_baggage_kg": sum(1 for o in result.observations if o.checkin_baggage_kg is not None),
                "flight_segments": sum(1 for o in result.observations if o.flight_segments)
            }
        }
        
        logger.info("Coverage Statistics:")
        logger.info(json.dumps(coverage, indent=2))
        
        # Save observations
        output_dir = Path("runtime/audit_reports")
        output_dir.mkdir(parents=True, exist_ok=True)
        report_file = output_dir / f"audit_report_{args.source}_DEL-BOM.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump([o.model_dump(mode="json") for o in result.observations], f, indent=2)
            
        logger.info(f"Audit report saved to {report_file}")
        
    except Exception as e:
        logger.error(f"Audit failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
