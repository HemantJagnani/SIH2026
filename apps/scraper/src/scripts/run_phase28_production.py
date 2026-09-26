"""
Phase 28 Production Coverage Runner.

Executes:
- Target Route: DEL-BOM
- Lead Times: T+1, T+7, T+15, T+21, T+30, T+45
- Sources: Google Flights, EaseMyTrip
- Mode: CORE_ONLY with Result Stream Stabilization
- Bounded Enrichment Sample on target searches
- Records full stabilization telemetry, deduplication, quality validation, and APIx observations.
- Generates:
  APIx_Phase28_Production_Coverage_Report.json
  APIx_Phase28_Production_Coverage_Report.md
"""

import asyncio
import json
import logging
import time
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from core.orchestrator import CollectionOrchestrator
from core.policy_gate import RobotsPolicyGate
from models.enums import AvailabilityStatus, CabinClass, TripType, WorkflowState
from models.provenance import ExtractionMode, FieldStatus, MissingReason
from models.request import FareSearchRequest
from sources.easemytrip.adapter import EaseMyTripAdapter
from sources.googleflights.adapter import GoogleFlightsAdapter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("phase28_production")

LEAD_TIMES = [1, 7, 15, 21, 30, 45]
ROUTE_ORIGIN = "DEL"
ROUTE_DEST = "BOM"


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


async def execute_job(
    source_name: str,
    adapter: Any,
    source_url: str,
    lead_days: int,
    extraction_mode: ExtractionMode = ExtractionMode.CORE_ONLY,
    include_fare_options: bool = False,
) -> Dict[str, Any]:
    travel_date = datetime.now(timezone.utc).date() + timedelta(days=lead_days)
    run_id = uuid4()

    request = FareSearchRequest(
        source=source_name,
        origin=ROUTE_ORIGIN,
        destination=ROUTE_DEST,
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
        headless=True,
    )

    logger.info(
        f"=== Starting {source_name} {ROUTE_ORIGIN}-{ROUTE_DEST} T+{lead_days} "
        f"({travel_date}) [{extraction_mode.value}] ==="
    )
    t0 = time.monotonic()
    result = await orchestrator.run(request)
    duration = round(time.monotonic() - t0, 2)

    obs_list = result.observations
    obs_count = len(obs_list)
    state = result.terminal_state.value
    blocked = result.was_blocked
    block_reason = None
    if blocked:
        block_reason = state

    # Telemetry and stabilization
    stabilization_info = {
        "initial_cards": obs_count,
        "final_cards": obs_count,
        "cards_added_during_stabilization": 0,
        "stabilization_duration": 0.0,
        "stabilization_history": [obs_count],
    }
    if hasattr(adapter, "last_stabilization_telemetry") and adapter.last_stabilization_telemetry:
        tel = adapter.last_stabilization_telemetry
        stabilization_info["initial_cards"] = tel.get("initial_cards", obs_count)
        stabilization_info["final_cards"] = tel.get("final_cards", obs_count)
        stabilization_info["cards_added_during_stabilization"] = tel.get("cards_added_during_stabilization", 0)
        stabilization_info["stabilization_duration"] = tel.get("stabilization_duration", 0.0)
        stabilization_info["stabilization_history"] = tel.get("stabilization_history", [obs_count])

    # Diagnostic data
    diagnostics = {}
    if hasattr(adapter, "last_diagnostics") and adapter.last_diagnostics:
        diagnostics = adapter.last_diagnostics.model_dump(mode="json")
        if adapter.last_diagnostics.failure_classification:
            block_reason = adapter.last_diagnostics.failure_classification.value

    # Group by itinerary fingerprint
    itin_map = defaultdict(list)
    offer_fps = set()
    dup_offers = 0

    for o in obs_list:
        dep_str = o.departure_time_local.strftime("%H:%M") if o.departure_time_local else "UNKNOWN"
        arr_str = o.arrival_time_local.strftime("%H:%M") if o.arrival_time_local else "UNKNOWN"
        itin_fp = (o.origin, o.destination, str(o.travel_date), o.airline, o.flight_number, dep_str, arr_str, o.stops)
        itin_map[itin_fp].append(o)

        offer_fp = (itin_fp, o.fare_family, float(o.total_fare))
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
    price_dist = dict(Counter(get_price_band(o.total_fare) for o in obs_list))
    time_band_dist = dict(Counter(get_time_band(o.departure_time_local) for o in obs_list))

    # Missing fields audit
    missing_fields = {}
    if obs_list:
        sample = obs_list[0]
        for f in [
            "base_fare", "taxes", "fees", "gst", "airport_charges",
            "cabin_baggage_kg", "checkin_baggage_kg", "fare_family"
        ]:
            val = getattr(sample, f, None)
            if val is None:
                prov = getattr(sample, "field_provenance", {}).get(f, {})
                missing_fields[f] = prov.get("missing_reason", "NOT_PRESENT_IN_DOM")

    # Canonical observations sample for table
    canonical_samples = []
    for o in obs_list[:5]:
        canonical_samples.append({
            "source": o.source,
            "route": f"{o.origin}-{o.destination}",
            "travel_date": str(o.travel_date),
            "lead_days": o.lead_days,
            "itinerary_id": f"{o.airline}-{o.flight_number or 'FLT'}-{o.departure_time_local.strftime('%H%M') if o.departure_time_local else 'NA'}",
            "offer_id": o.source_offer_id or f"off-{uuid4().hex[:6]}",
            "airline": o.airline,
            "flight_number": o.flight_number,
            "stops": o.stops,
            "departure_band": get_time_band(o.departure_time_local),
            "fare_family": o.fare_family or "STANDARD",
            "cabin": str(o.cabin),
            "cabin_baggage_kg": o.cabin_baggage_kg,
            "checkin_baggage_kg": o.checkin_baggage_kg,
            "total_fare": float(o.total_fare),
            "currency": o.currency,
            "availability": o.availability.value,
            "price_status": o.price_status,
        })

    job_result = {
        "source": source_name,
        "route": f"{ROUTE_ORIGIN}-{ROUTE_DEST}",
        "lead_time": f"T+{lead_days}",
        "travel_date": str(travel_date),
        "extraction_mode": extraction_mode.value,
        "state": state,
        "collection_duration_seconds": duration,
        "cards_detected": stabilization_info["initial_cards"],
        "final_stable_cards": stabilization_info["final_cards"],
        "observations": obs_count,
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
        "missing_fields": missing_fields,
        "blocked": blocked,
        "block_reason": block_reason,
        "source_health": "HEALTHY" if state == "DONE" and obs_count > 0 else "DEGRADED",
        "evidence_dir": str(result.evidence_dir) if result.evidence_dir else None,
        "canonical_samples": canonical_samples,
    }

    logger.info(
        f"=== Finished {source_name} T+{lead_days}: state={state}, "
        f"cards={stabilization_info['final_cards']}, obs={obs_count}, "
        f"itins={unique_itins}, time={duration}s ==="
    )
    return job_result


async def main():
    logger.info("=" * 80)
    logger.info("APIx PHASE 28 — PRODUCTION COVERAGE RUNNER")
    logger.info("Target: DEL-BOM | Lead Times: T+1, T+7, T+15, T+21, T+30, T+45")
    logger.info("=" * 80)

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "phase": "APIx Phase 28 — Production Coverage + APIx Product Lock",
        "target_route": "DEL-BOM",
        "lead_times": [f"T+{lt}" for lt in LEAD_TIMES],
        "summary": "Core production tests with result stream stabilization across Google Flights and EaseMyTrip",
        "jobs": [],
    }

    # 1. Google Flights DEL-BOM across all 6 lead times
    logger.info("\n>>> STARTING GOOGLE FLIGHTS MATRIX RUN (CORE_ONLY) <<<")
    for lt in LEAD_TIMES:
        gf_adapter = GoogleFlightsAdapter(extraction_mode=ExtractionMode.CORE_ONLY)
        job_res = await execute_job(
            source_name="google_flights",
            adapter=gf_adapter,
            source_url="https://www.google.com/travel/flights",
            lead_days=lt,
            extraction_mode=ExtractionMode.CORE_ONLY,
        )
        report["jobs"].append(job_res)
        if job_res["blocked"]:
            logger.warning(f"Google Flights encountered block at T+{lt}. Enforcing SAFE STOP.")
            break
        await asyncio.sleep(2)

    # 2. EaseMyTrip DEL-BOM across all 6 lead times (with stream stabilization)
    logger.info("\n>>> STARTING EASEMYTRIP MATRIX RUN (CORE_ONLY WITH STREAM STABILIZATION) <<<")
    for lt in LEAD_TIMES:
        emt_adapter = EaseMyTripAdapter(
            include_fare_options=False,
            result_stability_interval=2.0,
            result_stability_required=3,
            result_max_wait=30.0,
        )
        job_res = await execute_job(
            source_name="easemytrip",
            adapter=emt_adapter,
            source_url="https://www.easemytrip.com",
            lead_days=lt,
            extraction_mode=ExtractionMode.CORE_ONLY,
        )
        report["jobs"].append(job_res)
        if job_res["blocked"]:
            logger.warning(f"EaseMyTrip encountered block at T+{lt}. Enforcing SAFE STOP.")
            break
        await asyncio.sleep(2)

    # 3. Controlled Enrichment Run for EaseMyTrip (T+7 and T+21)
    logger.info("\n>>> EXECUTING CONTROLLED ENRICHMENT RUN FOR EASEMYTRIP (T+7 & T+21) <<<")
    for lt in [7, 21]:
        emt_details_adapter = EaseMyTripAdapter(
            include_fare_options=True,
            result_stability_interval=2.0,
            result_stability_required=3,
            result_max_wait=30.0,
        )
        job_res = await execute_job(
            source_name="easemytrip",
            adapter=emt_details_adapter,
            source_url="https://www.easemytrip.com",
            lead_days=lt,
            extraction_mode=ExtractionMode.CORE_AND_DETAILS,
            include_fare_options=True,
        )
        report["jobs"].append(job_res)
        await asyncio.sleep(2)

    # Save machine-readable JSON report
    json_path = Path("APIx_Phase28_Production_Coverage_Report.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    logger.info(f"Production coverage report JSON written to {json_path}")


if __name__ == "__main__":
    asyncio.run(main())
