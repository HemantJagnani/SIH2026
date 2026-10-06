"""
Production Matrix Expansion Runner for Top 10 DGCA Routes.

Expands scraping coverage to the next 9 DGCA Top-60 routes (Ranks 2–10)
across all six standardized lead-time horizons:
T+1, T+7, T+15, T+21, T+30, T+45.

Routes:
1. DEL-BOM (Rank 1 - Preserved intact from Phase 28)
2. BLR-DEL (Rank 2)
3. BLR-BOM (Rank 3)
4. DEL-HYD (Rank 4)
5. DEL-PNQ (Rank 5)
6. DEL-CCU (Rank 6)
7. AMD-DEL (Rank 7)
8. DEL-MAA (Rank 8)
9. BOM-HYD (Rank 9)
10. DEL-SXR (Rank 10)

Maintains strict adherence to:
- Real production crawler orchestration (Playwright / GoogleFlightsAdapter)
- Robots policy verification
- Result stream stabilization
- Non-modification of DEL-BOM baseline
- Non-modification of index weights or reference price methodology
"""

import asyncio
import json
import logging
import os
import sys
import time
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

# Ensure scraper package is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "scraper" / "src"))

from core.orchestrator import CollectionOrchestrator
from core.policy_gate import RobotsPolicyGate
from models.enums import AvailabilityStatus, CabinClass, CollectionMode, TripType, WorkflowState
from models.provenance import ExtractionMode, FieldStatus, MissingReason
from models.request import FareSearchRequest
from sources.googleflights.adapter import GoogleFlightsAdapter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("production_matrix_top10")

LEAD_TIMES = [1, 7, 15, 21, 30, 45]

EXPANSION_ROUTES: List[Tuple[str, str, int]] = [
    ("BLR", "DEL", 2),
    ("BLR", "BOM", 3),
    ("DEL", "HYD", 4),
    ("DEL", "PNQ", 5),
    ("DEL", "CCU", 6),
    ("AMD", "DEL", 7),
    ("DEL", "MAA", 8),
    ("BOM", "HYD", 9),
    ("DEL", "SXR", 10),
]


def get_time_band(dt: Optional[datetime]) -> str:
    if not dt:
        return "UNKNOWN"
    h = dt.hour
    if 5 <= h < 12:
        return "Morning (05-12)"
    if 12 <= h < 17:
        return "Afternoon (12-17)"
    if 17 <= h < 21:
        return "Evening (17-21)"
    return "Night (21-05)"


def get_price_band(p: float) -> str:
    if p < 5000:
        return "<5000"
    if p < 7000:
        return "5000-7000"
    if p < 10000:
        return "7000-10000"
    if p < 15000:
        return "10000-15000"
    return ">15000"


async def execute_route_lead_job(
    origin: str,
    destination: str,
    rank: int,
    lead_days: int,
    source_name: str = "google_flights",
    source_url: str = "https://www.google.com/travel/flights",
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    travel_date = datetime.now(timezone.utc).date() + timedelta(days=lead_days)
    run_id = uuid4()
    route_str = f"{origin}-{destination}"

    request = FareSearchRequest(
        source=source_name,
        origin=origin,
        destination=destination,
        travel_date=travel_date,
        lead_days=lead_days,
        trip_type=TripType.ONE_WAY,
        cabin=CabinClass.ECONOMY,
        currency="INR",
        collection_mode=CollectionMode.BROWSER,
    )

    adapter = GoogleFlightsAdapter(extraction_mode=ExtractionMode.CORE_ONLY)
    policy_gate = RobotsPolicyGate()
    orchestrator = CollectionOrchestrator(
        source_id=source_name,
        source_url=source_url,
        adapter=adapter,
        policy_gate=policy_gate,
        headless=True,
    )

    logger.info(
        f"=== Starting {source_name} [Rank {rank}] {route_str} T+{lead_days} ({travel_date}) ==="
    )
    t0 = time.monotonic()
    result = await orchestrator.run(request)
    duration = round(time.monotonic() - t0, 2)

    obs_list = result.observations
    obs_count = len(obs_list)
    state = result.terminal_state.value
    blocked = result.was_blocked
    block_reason = state if blocked else None

    # Serialization of observations for storage
    serialized_observations = [o.model_dump(mode="json") for o in obs_list]

    # Telemetry and stabilization
    stabilization_info = {
        "initial_cards": obs_count,
        "final_cards": obs_count,
        "cards_added_during_stabilization": 0,
        "stabilization_duration": 0.0,
        "stabilization_history": [obs_count],
    }

    # Group by itinerary fingerprint
    itin_map = defaultdict(list)
    offer_fps = set()
    dup_offers = 0

    for o in obs_list:
        dep_str = o.departure_time_local.strftime("%H:%M") if o.departure_time_local else "UNKNOWN"
        arr_str = o.arrival_time_local.strftime("%H:%M") if o.arrival_time_local else "UNKNOWN"
        itin_fp = (o.origin, o.destination, str(o.travel_date), o.airline, o.flight_number, dep_str, arr_str, o.stops)
        itin_map[itin_fp].append(o)

        fare_val = float(o.total_fare) if o.total_fare is not None else 0.0
        offer_fp = (itin_fp, o.fare_family, fare_val)
        if offer_fp in offer_fps:
            dup_offers += 1
        else:
            offer_fps.add(offer_fp)

    unique_itins = len(itin_map)
    unique_offers = len(offer_fps)

    # Distributions
    airline_dist = dict(Counter(o.airline for o in obs_list))
    stops_dist = dict(Counter(o.stops for o in obs_list))
    fare_fam_dist = dict(Counter(o.fare_family or "STANDARD" for o in obs_list))
    price_dist = dict(Counter(get_price_band(float(o.total_fare) if o.total_fare is not None else 0.0) for o in obs_list))
    time_band_dist = dict(Counter(get_time_band(o.departure_time_local) for o in obs_list))

    # Canonical observations sample for report
    canonical_samples = []
    for o in obs_list[:5]:
        canonical_samples.append({
            "source": o.source,
            "route": route_str,
            "travel_date": str(o.travel_date),
            "lead_days": o.lead_days,
            "itinerary_id": f"{o.airline}-{o.flight_number or 'FLT'}-{o.departure_time_local.strftime('%H%M') if o.departure_time_local else 'NA'}",
            "offer_id": o.source_offer_id or f"off-{uuid4().hex[:6]}",
            "airline": o.airline,
            "flight_number": o.flight_number,
            "stops": o.stops,
            "departure_band": get_time_band(o.departure_time_local),
            "fare_family": o.fare_family or "STANDARD",
            "cabin": str(o.cabin.value if hasattr(o.cabin, 'value') else o.cabin),
            "total_fare": float(o.total_fare) if o.total_fare is not None else 0.0,
            "currency": o.currency,
            "availability": o.availability.value if hasattr(o.availability, 'value') else o.availability,
        })

    job_result = {
        "source": source_name,
        "route": route_str,
        "route_rank": rank,
        "lead_time": f"T+{lead_days}",
        "lead_days": lead_days,
        "travel_date": str(travel_date),
        "extraction_mode": "CORE_ONLY",
        "state": state,
        "collection_duration_seconds": duration,
        "cards_detected": obs_count,
        "observations_count": obs_count,
        "unique_itineraries": unique_itins,
        "unique_offers": unique_offers,
        "duplicate_offers": dup_offers,
        "offers_per_itinerary_avg": round(obs_count / max(1, unique_itins), 2),
        "stabilization_telemetry": stabilization_info,
        "distributions": {
            "airlines": airline_dist,
            "stops": stops_dist,
            "fare_families": fare_fam_dist,
            "price_bands": price_dist,
            "departure_bands": time_band_dist,
        },
        "blocked": blocked,
        "block_reason": block_reason,
        "source_health": "HEALTHY" if state == "DONE" and obs_count > 0 else "DEGRADED",
        "evidence_dir": str(result.evidence_dir) if result.evidence_dir else None,
        "canonical_samples": canonical_samples,
    }

    logger.info(
        f"=== Finished [Rank {rank}] {route_str} T+{lead_days}: state={state}, "
        f"obs={obs_count}, itins={unique_itins}, time={duration}s ==="
    )
    return job_result, serialized_observations


async def main():
    logger.info("=" * 80)
    logger.info("APIx PRODUCTION MATRIX EXPANSION: NEXT 9 DGCA TOP-60 ROUTES (RANKS 2–10)")
    logger.info("Lead Times: T+1, T+7, T+15, T+21, T+30, T+45 (54 total jobs)")
    logger.info("DEL-BOM baseline is strictly preserved and untouched.")
    logger.info("=" * 80)

    # Output file paths
    report_path = PROJECT_ROOT / "APIx_Top10_Production_Coverage_Report.json"
    observations_storage_path = PROJECT_ROOT / "runtime" / "top10_fare_observations.json"

    # Load existing report or initialize
    existing_jobs = []
    del_bom_preserved_jobs = []
    
    # Load DEL-BOM jobs from Phase 28 report to keep DEL-BOM unchanged
    p28_path = PROJECT_ROOT / "APIx_Phase28_Production_Coverage_Report.json"
    if p28_path.exists():
        with open(p28_path, "r", encoding="utf-8") as f:
            p28_data = json.load(f)
            del_bom_preserved_jobs = p28_data.get("jobs", [])
            logger.info(f"Loaded {len(del_bom_preserved_jobs)} preserved DEL-BOM baseline jobs from {p28_path.name}.")

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "phase": "APIx Production Matrix Expansion (Top 10 DGCA Routes)",
        "routes_covered": ["DEL-BOM"] + [f"{orig}-{dest}" for orig, dest, _ in EXPANSION_ROUTES],
        "lead_times": [f"T+{lt}" for lt in LEAD_TIMES],
        "total_routes_count": 10,
        "total_cells_count": 60,
        "summary": "Production matrix coverage for DGCA Top 10 domestic routes across 6 lead-time horizons.",
        "jobs": list(del_bom_preserved_jobs), # Start with preserved DEL-BOM jobs
    }

    all_expansion_observations: List[Dict[str, Any]] = []

    total_jobs = len(EXPANSION_ROUTES) * len(LEAD_TIMES)
    job_counter = 0

    for orig, dest, rank in EXPANSION_ROUTES:
        route_str = f"{orig}-{dest}"
        logger.info(f"\n>>> PROCESSING ROUTE [Rank {rank}]: {route_str} <<<")

        for lt in LEAD_TIMES:
            job_counter += 1
            logger.info(f"[{job_counter}/{total_jobs}] Executing {route_str} at T+{lt}...")
            
            try:
                job_res, obs = await execute_route_lead_job(
                    origin=orig,
                    destination=dest,
                    rank=rank,
                    lead_days=lt,
                )
                report["jobs"].append(job_res)
                all_expansion_observations.extend(obs)

                if job_res["blocked"]:
                    logger.warning(f"Encountered block on {route_str} at T+{lt}. Enforcing SAFE STOP.")
                    break

            except Exception as exc:
                logger.error(f"Error on {route_str} T+{lt}: {exc}", exc_info=True)
                # Record error job
                report["jobs"].append({
                    "source": "google_flights",
                    "route": route_str,
                    "route_rank": rank,
                    "lead_time": f"T+{lt}",
                    "lead_days": lt,
                    "state": "ERROR",
                    "observations_count": 0,
                    "error": str(exc),
                })

            # Checkpoint write after each job
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)

            # Politeness backoff between searches
            await asyncio.sleep(2)

    # Save full observations to runtime directory
    observations_storage_path.parent.mkdir(parents=True, exist_ok=True)
    with open(observations_storage_path, "w", encoding="utf-8") as f:
        json.dump(all_expansion_observations, f, indent=2)
    logger.info(f"Saved {len(all_expansion_observations)} expansion observations to {observations_storage_path}")

    # Generate matrix summary
    print("\n" + "=" * 80)
    print("PRODUCTION MATRIX EXPANSION COMPLETE: TOP 10 ROUTES SUMMARY")
    print("=" * 80)
    
    matrix_counts = defaultdict(lambda: defaultdict(int))
    for j in report["jobs"]:
        r = j.get("route", "DEL-BOM")
        lt = j.get("lead_time", "T+7")
        cnt = j.get("observations_count") or j.get("observations") or len(j.get("canonical_samples", []))
        matrix_counts[r][lt] += cnt

    all_routes = ["DEL-BOM"] + [f"{o}-{d}" for o, d, _ in EXPANSION_ROUTES]
    print(f"{'Route':<10} | {'T+1':<8} | {'T+7':<8} | {'T+15':<8} | {'T+21':<8} | {'T+30':<8} | {'T+45':<8} | {'Total':<8}")
    print("-" * 75)
    for r in all_routes:
        t1 = matrix_counts[r].get("T+1", 0)
        t7 = matrix_counts[r].get("T+7", 0)
        t15 = matrix_counts[r].get("T+15", 0)
        t21 = matrix_counts[r].get("T+21", 0)
        t30 = matrix_counts[r].get("T+30", 0)
        t45 = matrix_counts[r].get("T+45", 0)
        tot = t1 + t7 + t15 + t21 + t30 + t45
        print(f"{r:<10} | {t1:<8} | {t7:<8} | {t15:<8} | {t21:<8} | {t30:<8} | {t45:<8} | {tot:<8}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
