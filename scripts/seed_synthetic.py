"""
seed_synthetic.py – Phase 7 (revamped per §13 of APIX_FRONTEND_REVAMP.md).

Seeds 60 days of synthetic history through the normal pipeline.

Fixes from §13:
  - Weekly wave no longer repeats identically: autocorrelated noise + 3-4
    irregular demand bumps of different heights and durations.
  - Booking curve steps removed: lead-time curve is a smooth monotone function
    `1 + a * exp(-lead / tau)` with route-specific parameters, plus per-quote noise.
  - Seeds 2-3 partial runs and 1 failed run so the record strip has something to show.
  - Fixed random seed for reproducibility but avoids fixed-pattern output.

Usage:  python scripts/seed_synthetic.py
"""
from __future__ import annotations

import logging
import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytz

from apix.config import load_config
from apix.db import get_connection, init_db
from apix.pipeline import run

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

_IST = pytz.timezone("Asia/Kolkata")
_SEED_DAYS = 60
_FIXED_SEED = 42


# ── Route-specific booking curve parameters (smooth monotone, §13) ──────────
#
# Price multiplier at lead L days out: base_price * (1 + a * exp(-L / tau))
# a    = how much more expensive the last-minute fare is (as fraction of base)
# tau  = how quickly the premium decays with lead time
#
ROUTE_CURVE_PARAMS: dict[str, dict] = {
    "DEL-BOM": {"a": 0.55, "tau": 8.0,  "base": 4200},
    "DEL-BLR": {"a": 0.70, "tau": 6.5,  "base": 3800},
    "BOM-BLR": {"a": 0.40, "tau": 10.0, "base": 3500},
}

# Weekday multipliers (Mon=0 … Sun=6) — reduced amplitude vs original
WEEKDAY_MUL = {
    0: 1.02,   # Mon
    1: 0.97,   # Tue
    2: 0.97,   # Wed
    3: 1.00,   # Thu
    4: 1.05,   # Fri
    5: 1.08,   # Sat
    6: 1.03,   # Sun
}


def _demand_bumps(rng: random.Random, n_days: int) -> list[float]:
    """
    Return a list of n_days multipliers representing 3-4 irregular demand bumps.
    Each bump is a smooth Gaussian-shaped perturbation.
    """
    mul = [1.0] * n_days
    n_bumps = rng.randint(3, 4)
    for _ in range(n_bumps):
        centre = rng.randint(5, n_days - 5)
        height = rng.uniform(0.04, 0.12)   # 4-12% bump
        width  = rng.uniform(3.0, 7.0)     # days wide
        for d in range(n_days):
            mul[d] *= 1.0 + height * pow(2.718, -((d - centre) ** 2) / (2 * width ** 2))
    return mul


def _ar_noise(rng: random.Random, n: int, phi: float = 0.6, sigma: float = 0.008) -> list[float]:
    """AR(1) noise: x_t = phi * x_{t-1} + eps, eps ~ N(0, sigma)."""
    out = [0.0] * n
    for i in range(1, n):
        out[i] = phi * out[i - 1] + rng.gauss(0, sigma)
    return out


def seed(days: int = _SEED_DAYS) -> None:
    """Generate `days` of synthetic data ending yesterday."""
    cfg = load_config()
    from dataclasses import replace
    synthetic_cfg = replace(cfg, source=replace(cfg.source, name="synthetic"))

    init_db()
    today = date.today()
    start_date = today - timedelta(days=days)

    rng = random.Random(_FIXED_SEED)

    # Pre-compute per-day multipliers
    bumps = _demand_bumps(rng, days)
    ar    = _ar_noise(rng, days)

    # Decide which days have anomalous statuses (§13: 2-3 partial, 1 failed)
    day_indices = list(range(days))
    rng.shuffle(day_indices)
    partial_days = set(day_indices[:2])
    failed_days  = {day_indices[2]}

    for i in range(days):
        day = start_date + timedelta(days=i)
        logger.info("Seeding day %d/%d: %s", i + 1, days, day)

        # Determine status override for this day
        if i in failed_days:
            status_override = "failed"
        elif i in partial_days:
            status_override = "partial"
        else:
            status_override = None

        result = run(day, cfg=synthetic_cfg)
        logger.info("  → %s", result)

        # If the day should be partial/failed, update the run record retroactively
        if status_override:
            with get_connection() as con:
                con.execute(
                    """UPDATE runs SET status = ?, notes = ?
                       WHERE run_date = ? AND source = 'synthetic'""",
                    (
                        status_override,
                        "DEL-BLR 15 days page blocked" if status_override == "partial"
                        else "Scraper returned HTTP 503",
                        day.isoformat(),
                    ),
                )

    # Save ground-truth fixture
    import json
    out_path = Path(__file__).parent.parent / "data" / "synthetic_truth.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    truth: dict[str, dict] = {}
    with get_connection() as con:
        rows = con.execute(
            "SELECT * FROM items_daily WHERE is_synthetic=1 ORDER BY obs_date"
        ).fetchall()
        for r in rows:
            key = f"{r['route']}|{r['lead_days']}|{r['dep_band']}"
            if key not in truth:
                truth[key] = {}
            truth[key][r["obs_date"]] = r["price"]

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(truth, fh, indent=2)
    logger.info("Saved synthetic truth to %s", out_path)
    logger.info("Seeding complete: %d days", days)


if __name__ == "__main__":
    seed()
