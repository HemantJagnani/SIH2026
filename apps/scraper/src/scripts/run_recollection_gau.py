"""
Targeted Recollection Runner for the 12 Guwahati (GAU) Matrix Cells.

Target Cells:
- DEL-GAU: T+1, T+7, T+15, T+21, T+30, T+45 (Rank 19)
- BLR-GAU: T+1, T+7, T+15, T+21, T+30, T+45 (Rank 53)

Requirements:
1. Uses the updated GoogleFlightsUrlBuilder with GAU -> 'Guwahati' resolution.
2. Standard browser collection flow via CollectionOrchestrator and GoogleFlightsAdapter.
3. Safe-stop on CAPTCHA / access block.
4. Output saved to separate recollection files without modifying baseline datasets.
"""

import asyncio
import json
import logging
import os
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "scraper" / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

from core.orchestrator import CollectionOrchestrator
from core.policy_gate import RobotsPolicyGate
from models.provenance import ExtractionMode
from models.request import FareSearchRequest
from sources.googleflights.adapter import GoogleFlightsAdapter
from sources.googleflights.url_builder import GoogleFlightsUrlBuilder
from reconciliation.policy import (
    is_foreign_transit_carrier,
    is_higher_fare_family,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("recollection_gau")

TARGET_ROUTES = [
    {"rank": 19, "origin": "DEL", "destination": "GAU", "route": "DEL-GAU"},
    {"rank": 53, "origin": "BLR", "destination": "GAU", "route": "BLR-GAU"},
]

LEAD_TIMES = [1, 7, 15, 21, 30, 45]

OUTPUT_REPORT_PATH = PROJECT_ROOT / "runtime" / "recollection_gau_12cells_report.json"
OUTPUT_OBS_PATH = PROJECT_ROOT / "runtime" / "recollection_gau_12cells_observations.json"


async def scrape_single_cell(
    origin: str,
    destination: str,
    rank: int,
    lead_days: int,
    policy_gate: RobotsPolicyGate,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    # Compute travel date matching production matrix standard (UTC base date + lead days)
    travel_date = datetime.now(timezone.utc).date() + timedelta(days=lead_days)
    route_str = f"{origin}-{destination}"

    request = FareSearchRequest(
        source="google_flights",
        origin=origin,
        destination=destination,
        travel_date=travel_date,
        lead_days=lead_days,
        trip_type="ONE_WAY",
        cabin="ECONOMY",
        adults=1,
        children=0,
        infants=0,
        currency="INR",
        collection_mode="BROWSER",
    )

    expected_url = GoogleFlightsUrlBuilder.build_url(request)
    logger.info(f"Target URL: {expected_url}")

    adapter = GoogleFlightsAdapter(extraction_mode=ExtractionMode.CORE_ONLY)
    orchestrator = CollectionOrchestrator(
        source_id="google_flights",
        source_url="https://www.google.com/travel/flights",
        adapter=adapter,
        policy_gate=policy_gate,
        headless=True,
    )

    t0 = time.monotonic()
    result = await orchestrator.run(request)
    duration = round(time.monotonic() - t0, 2)

    obs_list = result.observations
    obs_count = len(obs_list)
    state = result.terminal_state.value
    blocked = result.was_blocked

    # Serialize raw observations
    serialized_obs = []
    for o in obs_list:
        d = o.model_dump(mode="json")
        d["route"] = route_str
        d["lead_time"] = f"T+{lead_days}"
        d["lead_days"] = lead_days
        d["rank"] = rank
        serialized_obs.append(d)

    # Classify cell observations under standard APIx stratum governance
    seen_offers = set()
    valid_count = 0
    dup_count = 0
    hff_count = 0
    ft_count = 0
    classified_obs = []

    for d in serialized_obs:
        airline = (d.get("airline") or "").strip()
        fare_fam = (d.get("fare_family") or "").strip().upper()
        fare = float(d.get("total_fare") or 0.0)
        flight_num = d.get("flight_number") or ""
        dep_time = str(d.get("departure_time_local", ""))

        if is_foreign_transit_carrier(airline):
            status = "FOREIGN_TRANSIT"
            ft_count += 1
        elif is_higher_fare_family(fare_fam):
            status = "HIGHER_FARE_FAMILY"
            hff_count += 1
        else:
            offer_sig = (airline, flight_num, dep_time, fare)
            if offer_sig in seen_offers:
                status = "DUPLICATE"
                dup_count += 1
            else:
                seen_offers.add(offer_sig)
                status = "VALID_BASELINE"
                valid_count += 1

        d_classified = dict(d)
        d_classified["status"] = status
        classified_obs.append(d_classified)

    job_result = {
        "source": "google_flights",
        "route": route_str,
        "route_rank": rank,
        "lead_time": f"T+{lead_days}",
        "lead_days": lead_days,
        "travel_date": str(travel_date),
        "target_url": expected_url,
        "state": state,
        "collection_duration_seconds": duration,
        "cards_detected": obs_count,
        "raw_observations": obs_count,
        "valid_count": valid_count,
        "duplicate_count": dup_count,
        "higher_fare_count": hff_count,
        "foreign_transit_count": ft_count,
        "blocked": blocked,
        "block_reason": state if blocked else None,
        "evidence_dir": str(result.evidence_dir) if result.evidence_dir else None,
        "run_id": str(result.run_id) if hasattr(result, "run_id") and result.run_id else None,
        "error": result.error_message if hasattr(result, "error_message") else None,
    }

    return job_result, classified_obs


async def main():
    logger.info("=== Starting Targeted Production Recollection for 12 GAU Cells ===")
    policy_gate = RobotsPolicyGate()

    all_jobs = []
    all_observations = []
    safe_stop_triggered = False

    for target in TARGET_ROUTES:
        if safe_stop_triggered:
            break

        orig = target["origin"]
        dest = target["destination"]
        rank = target["rank"]
        route_str = target["route"]

        for lt in LEAD_TIMES:
            logger.info(f"\n--- Scraping {route_str} T+{lt} (Rank {rank}) ---")
            try:
                job_res, obs = await scrape_single_cell(
                    origin=orig,
                    destination=dest,
                    rank=rank,
                    lead_days=lt,
                    policy_gate=policy_gate,
                )
                all_jobs.append(job_res)
                all_observations.extend(obs)

                logger.info(
                    f"Result: state={job_res['state']}, cards={job_res['cards_detected']}, "
                    f"valid={job_res['valid_count']}, dups={job_res['duplicate_count']}, "
                    f"hff={job_res['higher_fare_count']}, ft={job_res['foreign_transit_count']}, "
                    f"blocked={job_res['blocked']}, time={job_res['collection_duration_seconds']}s"
                )

                if job_res["blocked"]:
                    logger.error(f"SAFE-STOP TRIGGERED: Block / protection state detected on {route_str} T+{lt}.")
                    safe_stop_triggered = True
                    break

            except Exception as e:
                logger.error(f"Exception during {route_str} T+{lt}: {e}", exc_info=True)
                all_jobs.append({
                    "source": "google_flights",
                    "route": route_str,
                    "route_rank": rank,
                    "lead_time": f"T+{lt}",
                    "lead_days": lt,
                    "state": "ERROR",
                    "cards_detected": 0,
                    "raw_observations": 0,
                    "valid_count": 0,
                    "duplicate_count": 0,
                    "higher_fare_count": 0,
                    "foreign_transit_count": 0,
                    "blocked": False,
                    "error": str(e),
                })

            # Save progress after every cell
            with open(OUTPUT_REPORT_PATH, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                        "target_cells_total": 12,
                        "completed_jobs": len(all_jobs),
                        "safe_stop_triggered": safe_stop_triggered,
                        "jobs": all_jobs,
                    },
                    f,
                    indent=2,
                )

            with open(OUTPUT_OBS_PATH, "w", encoding="utf-8") as f:
                json.dump(all_observations, f, indent=2)

            # Polite pacing between browser sessions
            await asyncio.sleep(3)

    logger.info("\n=== Recollection Complete ===")
    print("\n" + "=" * 105)
    print(f"{'Route':<10} {'Lead':<6} {'Cards':<6} {'RawObs':<8} {'Valid':<6} {'Dups':<6} {'HFF':<5} {'FT':<5} {'State':<8} {'Evidence Dir'}")
    print("=" * 105)
    for j in all_jobs:
        ev = j.get("evidence_dir", "")
        ev_short = Path(ev).name if ev else "None"
        print(f"{j['route']:<10} {j['lead_time']:<6} {j['cards_detected']:<6} {j['raw_observations']:<8} {j['valid_count']:<6} {j['duplicate_count']:<6} {j['higher_fare_count']:<5} {j['foreign_transit_count']:<5} {j['state']:<8} {ev_short}")
    print("=" * 105)


if __name__ == "__main__":
    asyncio.run(main())
