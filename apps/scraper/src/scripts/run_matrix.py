import asyncio
import logging
import argparse
from datetime import datetime
import json
import csv
from pathlib import Path
from uuid import uuid4

from core.job_generator import JobGenerator
from core.orchestrator import CollectionOrchestrator
from core.policy_gate import RobotsPolicyGate
from models.request import FareSearchRequest
from models.enums import WorkflowState
from sources.googleflights.adapter import GoogleFlightsAdapter
from sources.easemytrip.adapter import EaseMyTripAdapter

def setup_logging(log_level: str):
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    )

async def main():
    parser = argparse.ArgumentParser(description="Run Route x Lead-Time Matrix Orchestration")
    parser.add_argument("--source", type=str, default="google_flights", help="Source to run (google_flights or easemytrip)")
    parser.add_argument("--headed", action="store_true", help="Run in visible browser mode")
    parser.add_argument("--log-level", type=str, default="INFO", help="Logging level")
    parser.add_argument("--dry-run", action="store_true", help="Only generate jobs and check matrix completeness, do not execute scrape.")
    
    args = parser.parse_args()
    setup_logging(args.log_level)
    logger = logging.getLogger("run_matrix")
    
    # Setup generator and jobs
    generator = JobGenerator()
    jobs = generator.generate_jobs()
    
    # Filter by selected source
    jobs = [j for j in jobs if j["source"] == args.source]
    logger.info(f"Generated {len(jobs)} collection jobs for {args.source}.")
    
    # Setup adapter
    policy_gate = RobotsPolicyGate()
    
    if args.source == "google_flights":
        adapter = GoogleFlightsAdapter()
        source_url = "https://www.google.com/travel/flights"
    elif args.source == "easemytrip":
        adapter = EaseMyTripAdapter()
        source_url = "https://www.easemytrip.com"
    else:
        logger.error(f"Unknown source {args.source}")
        return

    orchestrator = CollectionOrchestrator(
        source_id=args.source,
        source_url=source_url,
        adapter=adapter,
        policy_gate=policy_gate,
        headless=not args.headed
    )

    collection_run_id = str(uuid4())
    stats = []

    logger.info("=" * 60)
    logger.info(f"Starting Matrix Run: {collection_run_id}")
    logger.info("=" * 60)

    for job_idx, job in enumerate(jobs, 1):
        origin = job["origin"]
        dest = job["destination"]
        travel_date = job["travel_date"]
        lead_days = job["lead_days"]
        
        logger.info(f"--- Running job {job_idx}/{len(jobs)}: {origin}-{dest} for T+{lead_days} ({travel_date}) ---")
        
        request = FareSearchRequest(**job)
        started_at = datetime.now()
        
        if args.dry_run:
            logger.info("DRY RUN: Skipping orchestration.")
            valid_obs = 0
            terminal_state = WorkflowState.DONE
            captcha_count = 0
            blocked_count = 0
            error_count = 0
            sold_out = 0
        else:
            try:
                result = await orchestrator.run(request)
                completed_at = datetime.now()
                
                valid_obs = len(result.observations)
                terminal_state = result.terminal_state
                
                captcha_count = 1 if terminal_state == WorkflowState.CAPTCHA_BLOCKED else 0
                blocked_count = 1 if terminal_state == WorkflowState.ACCESS_BLOCKED else 0
                error_count = 1 if terminal_state == WorkflowState.SEARCH_ERROR else 0
                sold_out = 1 if terminal_state == WorkflowState.NO_RESULTS else 0
            except Exception as e:
                logger.error(f"Job {job_idx} failed fatally: {e}")
                valid_obs = 0
                terminal_state = WorkflowState.SEARCH_ERROR
                captcha_count = 0
                blocked_count = 0
                error_count = 1
                sold_out = 0

        stat_record = {
            "collection_run_id": collection_run_id,
            "route": f"{origin}-{dest}",
            "origin": origin,
            "destination": dest,
            "travel_date": travel_date,
            "lead_days": lead_days,
            "search_timestamp": started_at.isoformat(),
            "requested": True,
            "started": not args.dry_run,
            "completed": not args.dry_run,
            "results_count": valid_obs,
            "valid_observations": valid_obs,
            "sold_out_count": sold_out,
            "captcha_count": captcha_count,
            "blocked_count": blocked_count,
            "parser_error_count": error_count,
            "terminal_state": "DRY_RUN" if args.dry_run else terminal_state.value
        }
        stats.append(stat_record)
            
    # Save the matrix summary
    output_dir = Path("runtime/matrix_reports")
    output_dir.mkdir(parents=True, exist_ok=True)
    report_file = output_dir / f"matrix_report_{collection_run_id}.csv"
    
    if stats:
        keys = stats[0].keys()
        with open(report_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(stats)
            
        logger.info(f"Matrix report saved to {report_file}")
        
    # Check completeness
    total_jobs = len(jobs)
    successful_jobs = sum(1 for s in stats if s["valid_observations"] > 0)
    blocked_jobs = sum(1 for s in stats if s["blocked_count"] > 0 or s["captcha_count"] > 0)
    
    logger.info("=" * 60)
    logger.info("MATRIX RUN COMPLETED")
    logger.info(f"Total Routes Scheduled:  {total_jobs}")
    logger.info(f"Successful Collections:  {successful_jobs}")
    logger.info(f"Blocked/Captcha:         {blocked_jobs}")
    logger.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
