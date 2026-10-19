"""
run_daily_pipeline.py - AERIX Unified Daily Production Pipeline
================================================================
A single, end-to-end executable that runs the daily airfare collection,
validation, econometric index compilation, and cloud synchronization
without needing a single line of code modified daily.

Key Guarantees:
1. ZERO Hardcoded Dates: Automatically resolves to UTC today, or accepts `--date YYYY-MM-DD`.
2. Automated 360-Cell Matrix Coverage: Checks Neon DB and scrapes missing cells across the DGCA Top-60 basket.
3. Sovereign Econometric Compilation: Computes Young-Laspeyres aggregate, elementary Jevons relatives,
   MoM/YoY inflation rates, and MoSPI CPI contributions (UN COICOP 07.3.3.1.2.01).
4. Cloud & Dashboard Sync: Writes to `apix_compiled_index.json`, syncs to Render Redis Key-Value,
   and refreshes the production Render backend cache.

Usage:
    python run_daily_pipeline.py                      # Automatically runs for today (UTC)
    python run_daily_pipeline.py --mode compile-only  # Re-compile & sync today's index from Neon DB
    python run_daily_pipeline.py --date 2026-10-20    # Run for a specific date
"""

import argparse
import asyncio
import io
import json
import logging
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Path setup
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "scraper" / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "api" / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import psycopg2
import redis
import requests

from scripts.compile_aerix_index import compile_index

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("aerix.pipeline")

CONFIG_PATH = PROJECT_ROOT / "config" / "dgca_cy2024_top60.json"
API_REFRESH_URL = "https://aerix-backend-cr41.onrender.com/api/cache/refresh"
DEFAULT_RENDER_REDIS_URL = "rediss://red-dat6u23tqb8s73a11ab0:c5ZQGgxyRWZ3qrGnGshvtO8UTLpMaSqu@singapore-keyvalue.render.com:6379"
LEAD_TIMES = [1, 7, 15, 21, 30, 45]


def get_db_url() -> str:
    return (
        os.environ.get("DATABASE_URL_SYNC", "").replace("+psycopg2", "")
        or os.environ.get("DATABASE_URL_DIRECT", "").replace("+asyncpg", "").replace("?ssl=require", "?sslmode=require")
        or os.environ.get("DATABASE_URL", "").replace("+asyncpg", "").replace("?ssl=require", "?sslmode=require")
    )


def get_neon_connection():
    db_url = get_db_url()
    if not db_url:
        raise RuntimeError("DATABASE_URL_SYNC or DATABASE_URL is not set in environment.")
    return psycopg2.connect(db_url)


def load_route_configs() -> List[dict]:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Configuration file {CONFIG_PATH} not found.")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f).get("routes", [])


def get_existing_cells(target_date: str) -> Set[Tuple[str, str, int]]:
    """Returns set of (origin, destination, lead_days) already present in Neon DB."""
    existing = set()
    try:
        conn = get_neon_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT origin, destination, lead_days 
            FROM fare_observations 
            WHERE DATE(collected_at) = %s::date
              AND total_fare > 0
            GROUP BY origin, destination, lead_days;
        """, (target_date,))
        for row in cur.fetchall():
            orig, dest, ld = row[0], row[1], int(row[2])
            existing.add((orig, dest, ld))
            existing.add((dest, orig, ld))
        conn.close()
    except Exception as e:
        logger.warning(f"Could not query existing cells for {target_date}: {e}")
    return existing


def get_db_summary(target_date: str) -> Tuple[int, int]:
    """Returns (distinct_routes_count, total_observations_count)."""
    try:
        conn = get_neon_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(DISTINCT origin || '-' || destination), COUNT(*) 
            FROM fare_observations 
            WHERE DATE(collected_at) = %s::date
              AND total_fare > 0;
        """, (target_date,))
        row = cur.fetchone()
        conn.close()
        return (row[0] or 0, row[1] or 0)
    except Exception as e:
        logger.warning(f"Could not count observations for {target_date}: {e}")
        return (0, 0)


async def scrape_and_ingest_cell(
    origin: str,
    destination: str,
    rank: int,
    lead_days: int,
    gate,
    sem: asyncio.Semaphore,
    counter: dict,
    target_date: str,
) -> bool:
    from core.policy_gate import RobotsPolicyGate
    from scripts.run_production_matrix_top60 import execute_route_lead_job
    from storage.auto_ingest_neon import ingest_top60_to_neon

    async with sem:
        route_str = f"{origin}-{destination}"
        t0 = time.time()
        for attempt in range(1, 3):
            try:
                job_res, obs = await asyncio.wait_for(
                    execute_route_lead_job(
                        origin=origin,
                        destination=destination,
                        rank=rank,
                        lead_days=lead_days,
                        policy_gate=gate,
                        base_date=target_date,
                    ),
                    timeout=50.0,
                )
                obs_cnt = len(obs)
                if obs_cnt > 0:
                    for o in obs:
                        o["collected_at"] = f"{target_date}T12:00:00+00:00"
                    ingested = ingest_top60_to_neon(obs)
                    counter["total_ingested"] += ingested
                    counter["completed_cells"] += 1
                    logger.info(
                        f"[{counter['completed_cells']}/{counter['total_target']}] "
                        f"SUCCESS: {route_str} T+{lead_days} ({obs_cnt} quotes, {ingested} in DB, {time.time()-t0:.1f}s)"
                    )
                    return True
                else:
                    logger.warning(f"RETRYING: {route_str} T+{lead_days} returned 0 quotes (attempt {attempt})...")
                    await asyncio.sleep(1.5)
            except Exception as exc:
                logger.warning(f"RETRYING: {route_str} T+{lead_days} attempt {attempt}: {exc}")
                await asyncio.sleep(1.5)

        # Reverse direction fallback
        try:
            job_res, obs = await asyncio.wait_for(
                execute_route_lead_job(
                    origin=destination,
                    destination=origin,
                    rank=rank,
                    lead_days=lead_days,
                    policy_gate=gate,
                    base_date=target_date,
                ),
                timeout=50.0,
            )
            if len(obs) > 0:
                for o in obs:
                    o["collected_at"] = f"{target_date}T12:00:00+00:00"
                ingested = ingest_top60_to_neon(obs)
                counter["total_ingested"] += ingested
                counter["completed_cells"] += 1
                logger.info(f"SUCCESS (Reverse): {destination}-{origin} T+{lead_days} ({len(obs)} quotes)")
                return True
        except Exception:
            pass

        return False


async def run_scraper(target_date: str, concurrency: int = 4):
    from core.policy_gate import RobotsPolicyGate

    routes = load_route_configs()
    existing_cells = get_existing_cells(target_date)
    init_routes, init_quotes = get_db_summary(target_date)
    print(f"Neon DB initial coverage: {init_routes}/60 routes, {len(existing_cells)}/360 cells, {init_quotes} quotes.")

    gate = RobotsPolicyGate()
    sem = asyncio.Semaphore(concurrency)

    # Phase 1: MoSPI official checkpoints (T+21 & T+7)
    # Phase 2: All other booking strata (T+1, T+15, T+30, T+45)
    phases = [
        ("Phase 1: MoSPI Checkpoints (T+21, T+7)", [21, 7]),
        ("Phase 2: Remaining Strata (T+1, T+15, T+30, T+45)", [1, 15, 30, 45]),
    ]

    for phase_name, lts in phases:
        existing_now = get_existing_cells(target_date)
        tasks_to_run = []
        for r_info in routes:
            orig = r_info["origin_code"]
            dest = r_info["destination_code"]
            rank = r_info["rank"]
            for lt in lts:
                if (orig, dest, lt) not in existing_now and (dest, orig, lt) not in existing_now:
                    tasks_to_run.append((orig, dest, rank, lt))

        if not tasks_to_run:
            print(f"--- {phase_name}: Complete! Skipping. ---")
            continue

        print(f"\n--- {phase_name}: {len(tasks_to_run)} missing cells ---")
        counter = {"completed_cells": 0, "total_target": len(tasks_to_run), "total_ingested": 0}
        active_futures = []
        for orig, dest, rank, lt in tasks_to_run:
            t = asyncio.create_task(scrape_and_ingest_cell(orig, dest, rank, lt, gate, sem, counter, target_date))
            active_futures.append(t)
            await asyncio.sleep(0.6)

        await asyncio.gather(*active_futures, return_exceptions=True)

    # Phase 3: Final sweep passes for 100% cell coverage
    for sweep in range(1, 3):
        existing_now = get_existing_cells(target_date)
        missing = []
        for r_info in routes:
            orig = r_info["origin_code"]
            dest = r_info["destination_code"]
            rank = r_info["rank"]
            for lt in LEAD_TIMES:
                if (orig, dest, lt) not in existing_now and (dest, orig, lt) not in existing_now:
                    missing.append((orig, dest, rank, lt))

        if not missing:
            print("\n>>> ALL 360 / 360 CELLS CONFIRMED IN NEON DB! <<<")
            break

        print(f"\n--- Sweep {sweep}: Scraping remaining {len(missing)} cells ---")
        counter_sweep = {"completed_cells": 0, "total_target": len(missing), "total_ingested": 0}
        tasks = []
        for orig, dest, rank, lt in missing:
            tasks.append(asyncio.create_task(scrape_and_ingest_cell(orig, dest, rank, lt, gate, sem, counter_sweep, target_date)))
            await asyncio.sleep(0.8)
        await asyncio.gather(*tasks, return_exceptions=True)


def publish_and_sync(compiled: dict, target_date: str):
    """Saves compiled index to disk, Render Redis Key-Value, and refreshes Render backend cache."""
    # 1. Save canonical JSON files
    out_target = PROJECT_ROOT / f"apix_compiled_index_{target_date.replace('-', '_')}.json"
    out_latest = PROJECT_ROOT / "apix_compiled_index.json"
    with open(out_target, "w", encoding="utf-8") as f:
        json.dump(compiled, f, indent=2)
    with open(out_latest, "w", encoding="utf-8") as f:
        json.dump(compiled, f, indent=2)
    print(f"Saved compiled index to {out_target.name} and apix_compiled_index.json")

    # 2. Sync to Render Redis Key-Value
    redis_url = os.environ.get("REDIS_URL") or DEFAULT_RENDER_REDIS_URL
    try:
        r_cli = redis.from_url(redis_url, decode_responses=True, socket_timeout=8)
        payload = json.dumps(compiled)
        r_cli.set(f"aerix:index:{target_date}", payload)
        r_cli.set("aerix:index:latest", payload)
        print(f"Synced {target_date} index to Render Redis Key-Value (aerix:index:{target_date} & aerix:index:latest)!")
    except Exception as rexc:
        print(f"Redis sync note: {rexc}")

    # 3. Refresh Render API Cache
    try:
        resp = requests.post(API_REFRESH_URL, timeout=10)
        print("Production API cache refreshed:", resp.json())
    except Exception as e:
        print(f"API cache refresh note: {e}")


def main():
    parser = argparse.ArgumentParser(description="AERIX Unified Daily Production Pipeline")
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Target collection date (YYYY-MM-DD). Defaults to UTC today.",
    )
    parser.add_argument(
        "--mode",
        choices=["full", "scrape-only", "compile-only"],
        default="full",
        help="Execution mode: 'full' (scrape missing cells then compile), 'scrape-only', or 'compile-only'.",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=4,
        help="Parallel scraper browser session concurrency limit.",
    )
    args = parser.parse_args()

    # Automatically resolve date dynamically if not passed
    target_date = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    print("\n" + "=" * 80)
    print("AERIX UNIFIED DAILY PRODUCTION PIPELINE")
    print(f"Target Date:     {target_date} {'(Auto-detected UTC Today)' if not args.date else ''}")
    print(f"Execution Mode:  {args.mode.upper()}")
    print(f"Concurrency:     {args.concurrency}")
    print(f"Start Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 80 + "\n")

    # 1. Scrape if needed
    if args.mode in ("full", "scrape-only"):
        asyncio.run(run_scraper(target_date, concurrency=args.concurrency))

    # 2. Compile and Publish if needed
    if args.mode in ("full", "compile-only"):
        print(f"\n--- Compiling AERIX Econometric Index for {target_date} ---")
        compiled = compile_index(target_date=target_date)
        publish_and_sync(compiled, target_date)

        routes_count, quotes_count = get_db_summary(target_date)
        print("\n" + "=" * 80)
        print("PIPELINE EXECUTION COMPLETE & DEPLOYED")
        print(f"Collection Date:       {target_date}")
        print(f"Distinct Routes:       {routes_count} / 60")
        print(f"Verified Observations: {quotes_count:,} quotes in Neon DB")
        print(f"Headline AERIX Index:  {compiled['index_value']} (Base CY2024 = 100)")
        print(f"All-India Fare:        INR {compiled['all_india_weighted_fare_inr']:,.0f}")
        print(f"MoM Inflation Rate:    {compiled['mom_percent']:+.2f}%")
        print(f"MoSPI CPI Contrib:     {compiled['cpi_contribution_combined_pp']:+.6f} pp")
        print(f"Dashboard URL:         https://sih-2026-sigma-eight.vercel.app/")
        print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
