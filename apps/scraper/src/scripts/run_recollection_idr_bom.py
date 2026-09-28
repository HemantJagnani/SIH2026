"""
Targeted Production Recollection Runner for IDR-BOM at T+7.

Target:
- Route: IDR-BOM (Rank 56)
- Lead Time: T+7
- Travel Date: 2026-10-04

Requirements:
- Production Google Flights workflow (CollectionOrchestrator, GoogleFlightsAdapter CORE_ONLY)
- Standard browser collection flow with full evidence capture
- Stop safely on error or protection state
- Save to separate output without modifying baseline
"""

import asyncio
import json
import logging
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

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
logger = logging.getLogger("recollection_idr_bom")

OUTPUT_PATH = PROJECT_ROOT / "runtime" / "recollection_idr_bom_t7_result.json"


async def main():
    logger.info("=== Starting Targeted Production Recollection for IDR-BOM T+7 ===")
    policy_gate = RobotsPolicyGate()

    travel_date = date(2026, 10, 4)
    origin = "IDR"
    destination = "BOM"
    lead_days = 7
    rank = 56
    route_str = "IDR-BOM"

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

    target_url = GoogleFlightsUrlBuilder.build_url(request)
    logger.info(f"Target URL: {target_url}")

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

    # Serialize observations
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
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source": "google_flights",
        "route": route_str,
        "route_rank": rank,
        "lead_time": f"T+{lead_days}",
        "lead_days": lead_days,
        "travel_date": str(travel_date),
        "target_url": target_url,
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
        "is_populated": (valid_count > 0),
        "observations": classified_obs,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(job_result, f, indent=2)

    logger.info(
        f"=== IDR-BOM T+7 Complete: state={state}, cards={obs_count}, "
        f"valid={valid_count}, dups={dup_count}, hff={hff_count}, ft={ft_count}, "
        f"blocked={blocked}, time={duration}s ==="
    )
    print("\n" + "=" * 90)
    print(f"Route: {route_str}")
    print(f"Lead Time: T+{lead_days} ({travel_date})")
    print(f"Terminal State: {state}")
    print(f"Cards Detected: {obs_count}")
    print(f"Raw Observations: {obs_count}")
    print(f"Valid Baseline: {valid_count}")
    print(f"Duplicates: {dup_count}")
    print(f"Higher Fare Family: {hff_count}")
    print(f"Foreign Transit: {ft_count}")
    print(f"Blocked: {blocked}")
    print(f"Run ID: {job_result['run_id']}")
    print(f"Evidence Dir: {job_result['evidence_dir']}")
    print(f"Is Populated: {job_result['is_populated']}")
    print("=" * 90)


if __name__ == "__main__":
    asyncio.run(main())
