"""
Data cleaning for APIx – Phase 3.

Takes raw Quote objects (as returned by sources) and applies:
1. Price string parsing (₹, commas) → float; sets parse_ok=False on failure
2. Base fare / tax split when available; else leaves null
3. Carrier name normalisation
4. Departure time normalisation to HH:MM 24h; assigns dep_band
5. Sold-out flag (kept as informative, not deleted)
6. Anomaly flagging: >7-day history required; IQR-like threshold vs. last-7-day median
"""
from __future__ import annotations

import logging
import re
import sqlite3
from datetime import date
from statistics import median
from typing import TYPE_CHECKING

from apix.models import Quote
from apix.db import get_items_before

logger = logging.getLogger(__name__)

# ── Carrier name normalisation map ────────────────────────────────────────
_CARRIER_ALIASES: dict[str, str] = {
    "indigo": "IndiGo",
    "6e": "IndiGo",
    "air india": "Air India",
    "ai": "Air India",
    "spicejet": "SpiceJet",
    "sg": "SpiceJet",
    "vistara": "Vistara",
    "uk": "Vistara",
    "goair": "GoAir",
    "g8": "GoAir",
    "go air": "GoAir",
    "akasa": "Akasa Air",
    "akasa air": "Akasa Air",
    "qp": "Akasa Air",
}

# Departure-band time boundaries (24h, inclusive start, exclusive end)
_BANDS = [
    ("morning",   "05:00", "12:00"),
    ("afternoon", "12:00", "18:00"),
    ("evening",   "18:00", "24:00"),
]


# ── Price parsing ─────────────────────────────────────────────────────────

def parse_price(raw: object) -> float | None:
    """
    Parse a price value into a float.

    Accepts:
      - int / float already
      - strings like "₹ 5,220", "5220.50", "5,220"
      - None → returns None (not a parse failure)

    Returns None with a logged warning if the string cannot be parsed.
    """
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        # Remove currency symbols, commas, and whitespace
        cleaned = re.sub(r"[₹,\s]", "", raw)
        try:
            return float(cleaned)
        except ValueError:
            logger.warning("Could not parse price %r", raw)
            return None
    logger.warning("Unexpected price type %r: %r", type(raw), raw)
    return None


# ── Departure time helpers ────────────────────────────────────────────────

def normalise_dep_time(raw: str | None) -> str | None:
    """
    Normalise a departure time string to HH:MM.

    Accepts: "06:30", "6:30", "06:30 AM", "6:30PM", etc.
    Returns None if unparseable.
    """
    if raw is None:
        return None
    raw = raw.strip()

    # Strip AM/PM
    am_pm = None
    m = re.search(r"(am|pm)$", raw, re.IGNORECASE)
    if m:
        am_pm = m.group(1).lower()
        raw = raw[: m.start()].strip()

    # Extract HH:MM or HH
    m2 = re.match(r"^(\d{1,2})(?::(\d{2}))?$", raw)
    if not m2:
        logger.warning("Could not parse dep_time %r", raw)
        return None

    hour = int(m2.group(1))
    minute = int(m2.group(2) or 0)

    if am_pm == "pm" and hour != 12:
        hour += 12
    if am_pm == "am" and hour == 12:
        hour = 0

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        logger.warning("dep_time out of range: %r", (hour, minute))
        return None

    return f"{hour:02d}:{minute:02d}"


def assign_dep_band(dep_time: str | None) -> str | None:
    """
    Assign morning / afternoon / evening band from an HH:MM dep_time.

    Returns None if dep_time is None or unparseable.
    """
    if dep_time is None:
        return None
    try:
        h, m = map(int, dep_time.split(":"))
    except ValueError:
        return None
    total_minutes = h * 60 + m
    if 5 * 60 <= total_minutes < 12 * 60:
        return "morning"
    if 12 * 60 <= total_minutes < 18 * 60:
        return "afternoon"
    if 18 * 60 <= total_minutes < 24 * 60:
        return "evening"
    return None  # before 05:00 (rare late-night departures)


# ── Carrier normalisation ─────────────────────────────────────────────────

def normalise_carrier(raw: str | None) -> str:
    if raw is None:
        return "Unknown"
    key = raw.strip().lower()
    return _CARRIER_ALIASES.get(key, raw.strip())


# ── Anomaly detection ─────────────────────────────────────────────────────

_ANOMALY_LOW = 0.4
_ANOMALY_HIGH = 2.5
_MIN_HISTORY_DAYS = 5


def _get_historical_prices(
    con: sqlite3.Connection,
    obs_date: date,
    route: str,
    lead_days: int,
    dep_band: str,
) -> list[float]:
    """
    Return item prices for the same (route, lead_days, dep_band) over the
    previous 7 days (not including obs_date).
    """
    rows = get_items_before(con, obs_date, route, lead_days, dep_band)
    return [float(r["price"]) for r in rows if r["price"] is not None]


def flag_anomalies(
    quotes: list[Quote],
    con: sqlite3.Connection | None = None,
) -> list[Quote]:
    """
    Flag quotes whose total_fare is an outlier vs. the last-7-day median
    for that (route, lead_days, dep_band) cell.

    The anomaly flag is set; the quote is NOT removed.
    Requires at least _MIN_HISTORY_DAYS of prior item prices.
    If no history or db is unavailable, no flagging is done.
    """
    if con is None:
        return quotes  # no history source → skip flagging

    # Group quotes by cell to avoid redundant DB queries
    cells_checked: dict[tuple, float | None] = {}

    for q in quotes:
        if q.total_fare is None or q.dep_band is None:
            continue

        cell_key = (q.route, q.lead_days, q.dep_band)
        if cell_key not in cells_checked:
            hist = _get_historical_prices(con, q.obs_date, q.route, q.lead_days, q.dep_band)
            if len(hist) < _MIN_HISTORY_DAYS:
                cells_checked[cell_key] = None  # not enough history
            else:
                cells_checked[cell_key] = median(hist)

        hist_median = cells_checked[cell_key]
        if hist_median is None or hist_median == 0:
            continue

        ratio = q.total_fare / hist_median
        if ratio < _ANOMALY_LOW or ratio > _ANOMALY_HIGH:
            q.anomaly_flag = True
            logger.info(
                "Anomaly flagged: %s %s lead=%d band=%s fare=%.0f median=%.0f ratio=%.2f",
                q.route, q.obs_date, q.lead_days, q.dep_band,
                q.total_fare, hist_median, ratio,
            )

    return quotes


# ── Main cleaning pipeline ────────────────────────────────────────────────

def clean_quotes(
    quotes: list[Quote],
    con: sqlite3.Connection | None = None,
) -> list[Quote]:
    """
    Apply all cleaning steps to a list of raw quotes in-place.

    Steps:
      1. Parse prices (total_fare; base_fare/taxes if present)
      2. Normalise carrier name
      3. Normalise dep_time to HH:MM; assign dep_band
      4. Mark sold_out
      5. Flag anomalies (requires history in DB)

    Returns the same list with fields mutated.
    """
    for q in quotes:
        # Step 1: price parsing
        total = parse_price(q.total_fare)
        if q.total_fare is not None and total is None:
            q.parse_ok = False
        q.total_fare = total

        q.base_fare = parse_price(q.base_fare)
        q.taxes = parse_price(q.taxes)

        # Step 2: carrier normalisation
        q.carrier = normalise_carrier(q.carrier)

        # Step 3: dep_time / dep_band
        q.dep_time = normalise_dep_time(q.dep_time)
        q.dep_band = assign_dep_band(q.dep_time)

        # Step 4: sold_out is already a bool; ensure it's set
        if q.sold_out is None:
            q.sold_out = False

    # Step 5: anomaly detection (needs DB history)
    quotes = flag_anomalies(quotes, con=con)

    return quotes
