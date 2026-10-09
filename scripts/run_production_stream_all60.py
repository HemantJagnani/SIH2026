"""
run_production_stream_all60.py - Live production runner for DGCA Top-60 routes.

Streams live Google Flights domestic quotes directly into hosted Neon PostgreSQL.
Enforces real-time per-cell DB ingestion and automatically refreshes API cache
once >= 50 distinct routes are logged to activate the live October 6 dataset on the frontend.
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import psycopg2
import requests
from dotenv import load_dotenv

# Path setup
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "scraper" / "src"))
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from core.policy_gate import RobotsPolicyGate
from scripts.run_production_matrix_top60 import execute_route_lead_job
from storage.auto_ingest_neon import ingest_top60_to_neon

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("stream_all60")

CONFIG_PATH = PROJECT_ROOT / "config" / "dgca_cy2024_top60.json"
API_REFRESH_URL = "https://aerix-backend-cr41.onrender.com/api/cache/refresh"
RAW_DB_URL = (
    os.environ.get("DATABASE_URL_SYNC", "").replace("+psycopg2", "")
    or os.environ.get("DATABASE_URL_DIRECT", "").replace("+asyncpg", "").replace("?ssl=require", "?sslmode=require")
    or os.environ.get("DATABASE_URL", "").replace("+asyncpg", "").replace("?ssl=require", "?sslmode=require")
)


def get_existing_cells_today(target_date: str = None):
    """Queries Neon DB for (origin, destination, lead_days) already collected today."""
    if not target_date:
        target_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    existing = set()
    try:
        conn = psycopg2.connect(RAW_DB_URL)
        cur = conn.cursor()
        cur.execute(f"""
            SELECT origin, destination, lead_days 
            FROM fare_observations 
            WHERE DATE(collected_at) = '{target_date}'::date
              AND total_fare > 0
            GROUP BY origin, destination, lead_days;
        """)
        for row in cur.fetchall():
            orig, dest, ld = row[0], row[1], int(row[2])
            existing.add((orig, dest, ld))
            existing.add((dest, orig, ld))
        conn.close()
    except Exception as e:
        logger.warning(f"Could not query existing cells: {e}")
    return existing


def get_today_distinct_routes_count(target_date: str = None):
    """Returns number of distinct routes collected today in Neon DB."""
    if not target_date:
        target_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        conn = psycopg2.connect(RAW_DB_URL)
        cur = conn.cursor()
        cur.execute(f"""
            SELECT COUNT(DISTINCT origin || '-' || destination), COUNT(*) 
            FROM fare_observations 
            WHERE DATE(collected_at) = '{target_date}'::date
              AND total_fare > 0;
        """)
        row = cur.fetchone()
        conn.close()
        return row[0] or 0, row[1] or 0
    except Exception as e:
        logger.warning(f"Could not count routes: {e}")
        return 0, 0


async def scrape_and_ingest_cell(origin, destination, rank, lead_days, gate, sem, counter):
    async with sem:
        route_str = f"{origin}-{destination}"
        t0 = time.time()
        # Attempt 1 & 2: Forward direction
        for attempt in range(1, 3):
            try:
                job_res, obs = await asyncio.wait_for(
                    execute_route_lead_job(
                        origin=origin,
                        destination=destination,
                        rank=rank,
                        lead_days=lead_days,
                        policy_gate=gate,
                    ),
                    timeout=50.0,
                )
                obs_cnt = len(obs)
                if obs_cnt > 0:
                    ingested = ingest_top60_to_neon(obs)
                    counter["total_ingested"] += ingested
                    counter["completed_cells"] += 1
                    logger.info(
                        f"[{counter['completed_cells']}/{counter['total_target']}] "
                        f"SUCCESS: {route_str} T+{lead_days} ({obs_cnt} quotes, {ingested} in DB, {time.time()-t0:.1f}s)"
                    )
                    return True
                else:
                    logger.warning(
                        f"RETRYING: {route_str} T+{lead_days} returned 0 quotes (state={job_res.get('state')}), attempt {attempt}..."
                    )
                    await asyncio.sleep(2.0)
            except asyncio.TimeoutError:
                logger.warning(f"TIMEOUT: {route_str} T+{lead_days} timed out on attempt {attempt}")
                await asyncio.sleep(2.0)
            except Exception as exc:
                logger.error(f"ERROR: {route_str} T+{lead_days} attempt {attempt}: {exc}")
                await asyncio.sleep(2.0)

        # Attempt 3: Fallback to reverse direction if forward returned 0
        try:
            logger.info(f"FALLBACK: Trying reverse direction {destination}-{origin} T+{lead_days}...")
            job_res, obs = await asyncio.wait_for(
                execute_route_lead_job(
                    origin=destination,
                    destination=origin,
                    rank=rank,
                    lead_days=lead_days,
                    policy_gate=gate,
                ),
                timeout=50.0,
            )
            obs_cnt = len(obs)
            if obs_cnt > 0:
                ingested = ingest_top60_to_neon(obs)
                counter["total_ingested"] += ingested
                counter["completed_cells"] += 1
                logger.info(
                    f"[{counter['completed_cells']}/{counter['total_target']}] "
                    f"SUCCESS (Reverse): {destination}-{origin} T+{lead_days} ({obs_cnt} quotes, {ingested} in DB)"
                )
                return True
            else:
                logger.warning(f"EMPTY: {destination}-{origin} T+{lead_days} returned 0 quotes on reverse fallback.")
        except asyncio.TimeoutError:
            logger.warning(f"TIMEOUT: {destination}-{origin} T+{lead_days} timed out on reverse fallback.")
        except Exception as exc:
            logger.error(f"ERROR reverse {destination}-{origin} T+{lead_days}: {exc}")

        return False


async def main():
    target_date = sys.argv[1] if len(sys.argv) > 1 else datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print("=" * 80)
    print("AERIX LIVE PRODUCTION STREAMER - DGCA CY2024 TOP-60 ROUTES")
    print(f"Target Date: {target_date} | Start Time: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 80)

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config_data = json.load(f)
    routes = config_data.get("routes", [])
    print(f"Loaded {len(routes)} routes from {CONFIG_PATH.name}")

    existing_cells = get_existing_cells_today(target_date)
    initial_routes, initial_quotes = get_today_distinct_routes_count(target_date)
    print(f"Initial Neon DB state for {target_date}: {initial_routes} distinct routes, {len(existing_cells)}/360 cells, {initial_quotes} quotes.")

    gate = RobotsPolicyGate()
    # Concurrency limit of 4 parallel browser sessions for high throughput
    sem = asyncio.Semaphore(4)

    # Lead times priority:
    # Phase 1: T+21 (MoSPI official specification) & T+7 (short horizon) across ALL 60 routes
    phase1_lead_times = [21, 7]
    # Phase 2: T+1, T+15, T+30, T+45 to complete the full 360-cell matrix
    phase2_lead_times = [1, 15, 30, 45]

    for phase_num, lts in [(1, phase1_lead_times), (2, phase2_lead_times)]:
        existing_now = get_existing_cells_today(target_date)
        tasks_to_run = []
        for r_info in routes:
            orig = r_info["origin_code"]
            dest = r_info["destination_code"]
            rank = r_info["rank"]
            for lt in lts:
                if (orig, dest, lt) in existing_now or (dest, orig, lt) in existing_now:
                    continue
                tasks_to_run.append((orig, dest, rank, lt))

        if not tasks_to_run:
            print(f"\n--- Phase {phase_num} already complete! Skipping. ---")
            continue

        print(f"\n--- Starting Phase {phase_num} ({len(tasks_to_run)} cells to scrape) ---")
        counter = {
            "completed_cells": 0,
            "total_target": len(tasks_to_run),
            "total_ingested": 0,
        }

        # Run tasks with concurrency
        active_futures = []
        for orig, dest, rank, lt in tasks_to_run:
            task = asyncio.create_task(
                scrape_and_ingest_cell(orig, dest, rank, lt, gate, sem, counter)
            )
            active_futures.append(task)
            await asyncio.sleep(0.8)  # Gentle stagger between spawns

            # Check distinct routes count periodically
            if len(active_futures) % 12 == 0:
                current_routes, current_quotes = get_today_distinct_routes_count(target_date)
                print(f"Progress Check: {current_routes}/60 distinct routes in DB ({current_quotes} quotes)")
                if current_routes >= 50:
                    try:
                        requests.post(API_REFRESH_URL, timeout=8)
                    except Exception:
                        pass

        await asyncio.gather(*active_futures, return_exceptions=True)

        final_routes, final_quotes = get_today_distinct_routes_count(target_date)
        print(f"\nPhase {phase_num} Completed!")
        print(f"Neon DB Status: {final_routes} distinct routes, {final_quotes} total quotes.")

        if final_routes >= 50:
            print(">>> Reached >= 50 routes! Triggering production API cache refresh... <<<")
            try:
                resp = requests.post(API_REFRESH_URL, timeout=10)
                print("API cache refreshed:", resp.json())
            except Exception as e:
                print("Cache refresh note:", e)

    # Phase 3: Guaranteed 100% 360-Cell Complete Sweep
    all_lts = [1, 7, 15, 21, 30, 45]
    for sweep_pass in range(1, 4):
        existing_now = get_existing_cells_today(target_date)
        missing_cells = []
        for r_info in routes:
            orig = r_info["origin_code"]
            dest = r_info["destination_code"]
            rank = r_info["rank"]
            for lt in all_lts:
                if (orig, dest, lt) not in existing_now and (dest, orig, lt) not in existing_now:
                    missing_cells.append((orig, dest, rank, lt))

        populated_cells_count = len(routes) * len(all_lts) - len(missing_cells)
        print(f"\n--- Matrix Status: {populated_cells_count}/360 cells populated ({len(missing_cells)} missing) ---")

        if not missing_cells:
            print(">>> ALL 360 / 360 CELLS CONFIRMED IN NEON POSTGRESQL! <<<")
            break

        print(f"\n--- Phase 3 (Sweep Pass {sweep_pass}): Scraping {len(missing_cells)} missing cells ---")
        counter_sweep = {
            "completed_cells": 0,
            "total_target": len(missing_cells),
            "total_ingested": 0,
        }
        sweep_tasks = []
        for orig, dest, rank, lt in missing_cells:
            task = asyncio.create_task(
                scrape_and_ingest_cell(orig, dest, rank, lt, gate, sem, counter_sweep)
            )
            sweep_tasks.append(task)
            await asyncio.sleep(1.0)

        await asyncio.gather(*sweep_tasks, return_exceptions=True)

    final_routes, final_quotes = get_today_distinct_routes_count(target_date)
    print("\n" + "=" * 80)
    print(f"ALL 60 ROUTES PROCESSED! Final Status: {final_routes}/60 routes, {final_quotes} quotes.")
    print("=" * 80)

    # Compilation & Publishing
    try:
        from scripts.compile_aerix_index import compile_index
        print(f"\nCompiling official AERIX headline index for {target_date}...")
        compiled = compile_index(target_date=target_date)
        out_target = PROJECT_ROOT / f"apix_compiled_index_{target_date.replace('-', '_')}.json"
        with open(out_target, "w", encoding="utf-8") as f:
            json.dump(compiled, f, indent=2)
        out_latest = PROJECT_ROOT / "apix_compiled_index.json"
        with open(out_latest, "w", encoding="utf-8") as f:
            json.dump(compiled, f, indent=2)
        print(f"Index compiled successfully: {compiled['index_value']} (Fare: INR {compiled['all_india_weighted_fare_inr']})")

        # Sync to Render Redis Key-Value
        try:
            import redis
            redis_url = "rediss://red-dat6u23tqb8s73a11ab0:c5ZQGgxyRWZ3qrGnGshvtO8UTLpMaSqu@singapore-keyvalue.render.com:6379"
            r_cli = redis.from_url(redis_url, decode_responses=True, socket_timeout=10)
            json_str = json.dumps(compiled)
            r_cli.set(f"aerix:index:{target_date}", json_str)
            r_cli.set("aerix:index:latest", json_str)
            print(f"Synced {target_date} index to Render Redis Key-Value!")
        except Exception as rexc:
            print(f"Redis sync note: {rexc}")

        # Invalidate Render backend cache
        try:
            resp = requests.post(API_REFRESH_URL, timeout=10)
            print("Production API cache refreshed:", resp.json())
        except Exception as e:
            print("Cache refresh note:", e)

    except Exception as e:
        logger.warning(f"Index compilation note: {e}")


if __name__ == "__main__":
    asyncio.run(main())
