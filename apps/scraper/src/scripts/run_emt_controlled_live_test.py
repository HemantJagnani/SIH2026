"""
Controlled Live Test for EaseMyTrip Lifecycle Recovery.

Runs:
- DEL-BOM T+7 CORE_ONLY
- If successful, DEL-BOM T+21 CORE_ONLY
- If successful, small CORE_AND_DETAILS sample
- Writes comprehensive results to run_report_emt.json and merges into run_report.json
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
from sources.easemytrip.adapter import EaseMyTripAdapter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("emt_controlled_live_test")


async def run_emt_job(
    origin: str,
    destination: str,
    lead_days: int,
    include_fare_options: bool = False,
    headless: bool = True,
) -> dict:
    travel_date = datetime.now(timezone.utc).date() + timedelta(days=lead_days)
    run_id = str(uuid4())

    request = FareSearchRequest(
        source="easemytrip",
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

    adapter = EaseMyTripAdapter(include_fare_options=include_fare_options)
    policy_gate = RobotsPolicyGate()
    orchestrator = CollectionOrchestrator(
        source_id="easemytrip",
        source_url="https://www.easemytrip.com",
        adapter=adapter,
        policy_gate=policy_gate,
        headless=headless,
    )

    mode_label = "CORE_AND_DETAILS" if include_fare_options else "CORE_ONLY"
    logger.info(f"--- Running EaseMyTrip {origin}->{destination} T+{lead_days} ({mode_label}) ---")
    result = await orchestrator.run(request)

    obs_list = result.observations
    obs_count = len(obs_list)
    state = result.terminal_state.value
    blocked = result.was_blocked
    block_reason = None
    if blocked:
        block_reason = state

    diagnostics = {}
    if hasattr(adapter, "last_diagnostics") and adapter.last_diagnostics:
        diagnostics = adapter.last_diagnostics.model_dump(mode="json")
        if adapter.last_diagnostics.failure_classification:
            block_reason = adapter.last_diagnostics.failure_classification.value

    # Extract field presence
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

    job_result = {
        "source": "easemytrip",
        "route": f"{origin}-{destination}",
        "lead_time": f"T+{lead_days}",
        "travel_date": str(travel_date),
        "extraction_mode": mode_label,
        "state": state,
        "observations": obs_count,
        "enrichment_success": sum(1 for o in obs_list if o.fare_family and o.fare_family != "UNKNOWN"),
        "enrichment_failure": 0,
        "blocked": blocked,
        "block_reason": block_reason,
        "fields_extracted": sorted(list(fields_extracted)),
        "fields_unavailable": fields_unavailable,
        "diagnostics": diagnostics,
        "evidence_dir": str(result.evidence_dir) if result.evidence_dir else None,
    }
    return job_result


async def main():
    logger.info("=" * 70)
    logger.info("STARTING EASEMYTRIP CONTROLLED LIVE TEST")
    logger.info("=" * 70)

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "summary": "Controlled live test for EaseMyTrip Normal User Search Lifecycle Recovery",
        "jobs": [],
    }

    # Step 1: DEL-BOM T+7 (CORE_ONLY)
    t7_core = await run_emt_job(
        origin="DEL",
        destination="BOM",
        lead_days=7,
        include_fare_options=False,
    )
    report["jobs"].append(t7_core)
    print(f"\n[Result T+7 CORE_ONLY] State: {t7_core['state']}, Observations: {t7_core['observations']}")

    # Check safe-stop rule
    if t7_core["blocked"] or t7_core["state"] in ("CAPTCHA_BLOCKED", "ACCESS_BLOCKED", "SEARCH_ERROR"):
        logger.warning(f"EaseMyTrip halted at T+7 ({t7_core['block_reason']}). SAFE STOP ENFORCED.")
    else:
        # Step 2: DEL-BOM T+21 (CORE_ONLY)
        logger.info("\nT+7 CORE_ONLY succeeded! Proceeding to DEL-BOM T+21 (CORE_ONLY)...")
        t21_core = await run_emt_job(
            origin="DEL",
            destination="BOM",
            lead_days=21,
            include_fare_options=False,
        )
        report["jobs"].append(t21_core)
        print(f"\n[Result T+21 CORE_ONLY] State: {t21_core['state']}, Observations: {t21_core['observations']}")

        # Step 3: DEL-BOM T+7 (CORE_AND_DETAILS with multi-fare options)
        if not t21_core["blocked"] and t21_core["state"] == "DONE":
            logger.info("\nBoth CORE_ONLY searches succeeded! Testing CORE_AND_DETAILS sample...")
            t7_details = await run_emt_job(
                origin="DEL",
                destination="BOM",
                lead_days=7,
                include_fare_options=True,
            )
            report["jobs"].append(t7_details)
            print(f"\n[Result T+7 CORE_AND_DETAILS] State: {t7_details['state']}, Observations: {t7_details['observations']}")

    # Save to run_report_emt.json
    output_path = Path("run_report_emt.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # Also update run_report.json if exists
    main_report_path = Path("run_report.json")
    if main_report_path.exists():
        try:
            with open(main_report_path, "r", encoding="utf-8") as f:
                main_report = json.load(f)
            # Filter out old easemytrip jobs and append new ones
            main_report["jobs"] = [j for j in main_report.get("jobs", []) if j.get("source") != "easemytrip"]
            main_report["jobs"].extend(report["jobs"])
            with open(main_report_path, "w", encoding="utf-8") as f:
                json.dump(main_report, f, indent=2)
            logger.info("Updated main run_report.json with EaseMyTrip results.")
        except Exception as exc:
            logger.warning(f"Could not merge into run_report.json: {exc}")

    logger.info("=" * 70)
    logger.info(f"EASEMYTRIP LIVE TEST COMPLETE. Report saved to {output_path}")
    logger.info("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
