"""
Controlled Live Test Runner (Phase 26).

Runs:
- Route: DEL-BOM
- Lead times: T+7, T+21
- Sources: Google Flights, EaseMyTrip
- Mode: CORE_ONLY first, then small CORE_AND_DETAILS sample.
- If blocked: STOP immediately. Record diagnostics and permitted evidence. Never retry.
- Produces: run_report.json
"""

import asyncio
import json
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from core.orchestrator import CollectionOrchestrator
from core.policy_gate import RobotsPolicyGate
from models.enums import WorkflowState
from models.provenance import ExtractionMode
from models.request import FareSearchRequest
from sources.googleflights.adapter import GoogleFlightsAdapter
from sources.easemytrip.adapter import EaseMyTripAdapter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("controlled_live_test")


async def run_single_job(
    source_name: str,
    adapter,
    source_url: str,
    origin: str,
    destination: str,
    lead_days: int,
    extraction_mode: ExtractionMode = ExtractionMode.CORE_ONLY,
    headless: bool = True,
) -> dict:
    travel_date = datetime.now(timezone.utc).date() + timedelta(days=lead_days)
    run_id = uuid4()

    request = FareSearchRequest(
        source=source_name,
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

    policy_gate = RobotsPolicyGate()
    orchestrator = CollectionOrchestrator(
        source_id=source_name,
        source_url=source_url,
        adapter=adapter,
        policy_gate=policy_gate,
        headless=headless,
    )

    logger.info(f"--- Running {source_name} {origin}->{destination} T+{lead_days} ({extraction_mode.value}) ---")
    result = await orchestrator.run(request)

    obs_list = result.observations
    obs_count = len(obs_list)
    state = result.terminal_state.value
    blocked = result.was_blocked
    block_reason = None
    if blocked:
        block_reason = state

    # Check adapter diagnostics if available (e.g. for EaseMyTrip)
    diagnostics = {}
    if hasattr(adapter, "last_diagnostics") and adapter.last_diagnostics:
        diagnostics = adapter.last_diagnostics.model_dump(mode="json")
        if adapter.last_diagnostics.failure_classification:
            block_reason = adapter.last_diagnostics.failure_classification.value

    # Analyze extracted vs unavailable fields
    fields_extracted = set()
    fields_unavailable = {}

    if obs_list:
        sample = obs_list[0]
        for field in [
            "origin", "destination", "travel_date", "airline", "flight_number",
            "departure_time_local", "arrival_time_local", "stops", "total_fare",
            "currency", "base_fare", "taxes", "fees", "gst", "cabin_baggage_kg",
            "checkin_baggage_kg", "fare_family"
        ]:
            val = getattr(sample, field, None)
            if val is not None:
                fields_extracted.add(field)
            else:
                prov = getattr(sample, "field_provenance", {}).get(field, {})
                fields_unavailable[field] = prov.get("missing_reason", "NOT_PRESENT_IN_DOM")

    return {
        "source": source_name,
        "route": f"{origin}-{destination}",
        "lead_time": f"T+{lead_days}",
        "travel_date": str(travel_date),
        "extraction_mode": extraction_mode.value,
        "state": state,
        "observations": obs_count,
        "enrichment_success": sum(1 for o in obs_list if o.flight_segments) if obs_list else 0,
        "enrichment_failure": 0,
        "blocked": blocked,
        "block_reason": block_reason,
        "fields_extracted": sorted(list(fields_extracted)),
        "fields_unavailable": fields_unavailable,
        "diagnostics": diagnostics,
        "evidence_dir": str(result.evidence_dir) if result.evidence_dir else None,
    }


async def main():
    logger.info("=" * 70)
    logger.info("STARTING PHASE 26 CONTROLLED LIVE TEST")
    logger.info("=" * 70)

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "summary": "Controlled live test for Google Flights and EaseMyTrip",
        "jobs": [],
    }

    # -----------------------------------------------------------------------
    # 1. Google Flights Test: DEL-BOM T+7 (CORE_ONLY)
    # -----------------------------------------------------------------------
    gf_adapter_core = GoogleFlightsAdapter(extraction_mode=ExtractionMode.CORE_ONLY)
    gf_t7 = await run_single_job(
        source_name="google_flights",
        adapter=gf_adapter_core,
        source_url="https://www.google.com/travel/flights",
        origin="DEL",
        destination="BOM",
        lead_days=7,
        extraction_mode=ExtractionMode.CORE_ONLY,
    )
    report["jobs"].append(gf_t7)

    # If Google Flights is not blocked, test a small CORE_AND_DETAILS sample
    if not gf_t7["blocked"] and gf_t7["observations"] > 0:
        logger.info("Google Flights CORE_ONLY succeeded. Testing small CORE_AND_DETAILS sample...")
        gf_adapter_details = GoogleFlightsAdapter(extraction_mode=ExtractionMode.CORE_AND_DETAILS)
        gf_t7_details = await run_single_job(
            source_name="google_flights",
            adapter=gf_adapter_details,
            source_url="https://www.google.com/travel/flights",
            origin="DEL",
            destination="BOM",
            lead_days=7,
            extraction_mode=ExtractionMode.CORE_AND_DETAILS,
        )
        report["jobs"].append(gf_t7_details)

    # Google Flights T+21 (CORE_ONLY)
    if not gf_t7["blocked"]:
        gf_t21 = await run_single_job(
            source_name="google_flights",
            adapter=gf_adapter_core,
            source_url="https://www.google.com/travel/flights",
            origin="DEL",
            destination="BOM",
            lead_days=21,
            extraction_mode=ExtractionMode.CORE_ONLY,
        )
        report["jobs"].append(gf_t21)

    # -----------------------------------------------------------------------
    # 2. EaseMyTrip Test: DEL-BOM T+7 (CORE_ONLY)
    # -----------------------------------------------------------------------
    emt_adapter = EaseMyTripAdapter()
    emt_t7 = await run_single_job(
        source_name="easemytrip",
        adapter=emt_adapter,
        source_url="https://www.easemytrip.com",
        origin="DEL",
        destination="BOM",
        lead_days=7,
        extraction_mode=ExtractionMode.CORE_ONLY,
    )
    report["jobs"].append(emt_t7)

    # PHASE 26 Safe Stop Rule:
    # "For EaseMyTrip: if blocked: STOP. Do not repeatedly retry."
    if emt_t7["blocked"] or emt_t7["state"] in ("CAPTCHA_BLOCKED", "ACCESS_BLOCKED", "SEARCH_ERROR"):
        logger.warning(
            f"EaseMyTrip was blocked/halted ({emt_t7['block_reason']}). "
            "SAFE STOP ENFORCED: Skipping further EaseMyTrip searches without retrying."
        )
    else:
        # Only run T+21 if T+7 succeeded without blocking
        emt_t21 = await run_single_job(
            source_name="easemytrip",
            adapter=emt_adapter,
            source_url="https://www.easemytrip.com",
            origin="DEL",
            destination="BOM",
            lead_days=21,
            extraction_mode=ExtractionMode.CORE_ONLY,
        )
        report["jobs"].append(emt_t21)

    # Save run_report.json
    output_path = Path("run_report.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    logger.info("=" * 70)
    logger.info(f"CONTROLLED LIVE TEST COMPLETED. Report saved to {output_path}")
    logger.info("=" * 70)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
