"""
backfill_real.py – clear all synthetic/fixture data, then scrape real fares
from flight.easemytrip.com for the past N days.

Usage:
    python scripts/backfill_real.py --days 30
    python scripts/backfill_real.py --days 7   (quick test)

Each day's pipeline run scrapes DEL-BOM, DEL-BLR, BOM-BLR for 4 lead windows
(T+1, T+7, T+15, T+30).  Runs are spaced with a random 8–15 s delay between
each page fetch (configured in config.yaml).
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytz
from apix.config import load_config
from apix.db import get_connection, init_db
from apix.pipeline import run

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("backfill")


def wipe_mock_data() -> int:
    """Delete all synthetic and fixture rows from every derived table."""
    with get_connection() as con:
        # Quotes flagged synthetic or sourced from fixture
        n_quotes = con.execute(
            "DELETE FROM quotes WHERE is_synthetic = 1 OR source IN ('synthetic', 'fixture')"
        ).rowcount

        # Runs whose source is synthetic or fixture
        n_runs = con.execute(
            "DELETE FROM runs WHERE source IN ('synthetic', 'fixture')"
        ).rowcount

        # Derived tables — rebuild from scratch after live ingestion
        con.execute("DELETE FROM items_daily")
        con.execute("DELETE FROM item_relatives")
        con.execute("DELETE FROM index_daily")
        con.execute("DELETE FROM raw_responses")

    logger.info("Wiped %d synthetic/fixture quotes across %d runs", n_quotes, n_runs)
    return n_quotes


def backfill(days: int, dry_run: bool = False) -> None:
    init_db()
    cfg = load_config()

    # Verify source is set to easemytrip
    if cfg.source.name != "easemytrip":
        logger.warning(
            "config.yaml source.name is '%s', not 'easemytrip'. "
            "Set source.name: easemytrip before backfilling.",
            cfg.source.name,
        )
        if not dry_run:
            sys.exit(1)

    IST = pytz.timezone("Asia/Kolkata")
    today = date.today()

    # Dates to backfill: (today - days + 1) .. today, oldest first
    target_dates = [today - timedelta(days=i) for i in range(days - 1, -1, -1)]

    logger.info(
        "Backfilling %d days (%s → %s) using source='%s'",
        len(target_dates),
        target_dates[0],
        target_dates[-1],
        cfg.source.name,
    )

    if dry_run:
        logger.info("[DRY RUN] Would run: %s", target_dates)
        return

    # Skip dates that already have a successful live run
    with get_connection() as con:
        existing = {
            row[0]
            for row in con.execute(
                "SELECT run_date FROM runs WHERE source='easemytrip' AND status IN ('ok','partial')"
            ).fetchall()
        }

    skipped = 0
    for run_date in target_dates:
        ds = run_date.isoformat()
        if ds in existing:
            logger.info("  %s — already has live data, skipping", ds)
            skipped += 1
            continue

        logger.info("  %s — running pipeline …", ds)
        result = run(run_date, cfg=cfg)
        logger.info(
            "    → status=%s pages_ok=%d pages_failed=%d",
            result["status"], result["pages_ok"], result["pages_failed"],
        )

        if result["pages_ok"] == 0:
            logger.warning("    No pages scraped for %s — bot protection or all blocked", ds)

        # Polite pause between days (on top of per-page delays in the scraper)
        if ds != target_dates[-1].isoformat():
            pause = 20
            logger.info("    Pausing %ds before next day…", pause)
            time.sleep(pause)

    logger.info(
        "Backfill complete. Processed %d days, skipped %d already-done.",
        len(target_dates) - skipped,
        skipped,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Wipe mock data and backfill real fares")
    parser.add_argument("--days", type=int, default=14,
                        help="How many days to backfill (default: 14)")
    parser.add_argument("--no-wipe", action="store_true",
                        help="Skip wiping synthetic/fixture data")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would happen without scraping")
    args = parser.parse_args()

    if not args.no_wipe:
        logger.info("Wiping all synthetic and fixture data…")
        wipe_mock_data()

    backfill(days=args.days, dry_run=args.dry_run)
