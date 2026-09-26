"""
run_once.py — Daily batch pipeline runner.
Executed automatically by the daily scheduled task or manual CLI trigger.
Normalizes latest collections, runs index engine computation, and exports latest APIx series.
"""

import sys
import logging
from pathlib import Path

# Configure paths
sys.path.insert(0, str(Path("apps/scraper/src").resolve()))
sys.path.insert(0, str(Path(".").resolve()))

from scripts.normalize_dataset import main as run_normalize
from scripts.compute_index import main as run_compute

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("run_once")

def main():
    logger.info("==================================================")
    logger.info("Starting Daily APIx Batch Pipeline Run")
    logger.info("==================================================")

    # 1. Normalize dataset
    logger.info("Step 1: Normalizing dataset...")
    try:
        run_normalize()
    except Exception as exc:
        logger.error(f"Error during normalization: {exc}")
        sys.exit(1)

    # 2. Compute index
    logger.info("\nStep 2: Computing APIx Index...")
    try:
        run_compute()
    except Exception as exc:
        logger.error(f"Error during index computation: {exc}")
        sys.exit(1)

    logger.info("==================================================")
    logger.info("Daily APIx Pipeline Run Completed Successfully")
    logger.info("==================================================")

if __name__ == "__main__":
    main()
