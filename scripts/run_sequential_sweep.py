"""
run_sequential_sweep.py - Automated sequential scraper for October 10 and October 11, 2026.

Collects all 360 DGCA CY2024 Top-60 matrix cells for:
1. 2026-10-10 (Backfilled lead-time sweep)
2. 2026-10-11 (Live production sweep for Today)

Automatically handles index compilation, Redis synchronization, and live API cache invalidation.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Path setup
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from scripts.run_production_stream_all60 import run_stream

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("sequential_runner")


async def main():
    target_dates = ["2026-10-10", "2026-10-11"]
    
    for idx, target_date in enumerate(target_dates, 1):
        print("\n" + "#" * 80)
        print(f"### STEP {idx}/{len(target_dates)}: RUNNING AIRFARE SWEEP FOR {target_date} ###")
        print("#" * 80 + "\n")
        
        try:
            await run_stream(target_date=target_date)
            print(f"\nSuccessfully finished sweep and compilation for {target_date}!")
        except Exception as exc:
            logger.error(f"Error occurred during sweep for {target_date}: {exc}", exc_info=True)
            print(f"Sweep for {target_date} had an exception: {exc}")

        # Short rest between days to ensure clean connection resets
        await asyncio.sleep(5.0)

    print("\n" + "=" * 80)
    print("ALL SEQUENTIAL SWEEPS COMPLETED FOR 2026-10-10 AND 2026-10-11!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
