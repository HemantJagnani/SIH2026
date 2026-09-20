"""
FastAPI application – Phase 6.

Endpoints:
  GET /api/index        – overall or route index (daily/weekly/monthly)
  GET /api/items        – item prices for a specific date
  GET /api/lead-curve   – price vs. lead_days by day (for ridgeline)
  GET /api/relatives    – item relatives (for recomputing index in browser)
  GET /api/runs         – run history
  GET /api/methodology  – weights, rules, base date, assumptions
"""
from __future__ import annotations

import math
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from apix.config import load_config
from apix.db import get_connection, init_db

app = FastAPI(
    title="APIx – Airfare Price Index",
    description="REST API for the Indian domestic airfare price index prototype.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Ensure tables exist when the app starts
init_db()
cfg = load_config()


# ── Helpers ────────────────────────────────────────────────────────────────

def _iso_week(d: date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def _month_key(d: date) -> str:
    return f"{d.year}-{d.month:02d}"


# ── Endpoints ─────────────────────────────────────────────────────────────

@app.get("/api/index")
def get_index(
    scope: str = Query("overall", description="overall | route"),
    route: Optional[str] = Query(None, description="route id, required when scope=route"),
    freq: str = Query("daily", description="daily | weekly | monthly"),
):
    """
    Return time-series index levels.

    For weekly/monthly: geometric mean of daily levels in the period.
    Published only when at least 3 daily levels exist (else marked partial).
    """
    if scope == "route" and not route:
        raise HTTPException(status_code=422, detail="route is required when scope=route")

    with get_connection() as con:
        rows = con.execute(
            "SELECT * FROM index_daily WHERE scope=? ORDER BY obs_date",
            (scope,),
        ).fetchall()

    if scope == "route" and route:
        rows = [r for r in rows if r["route"] == route]

    if freq == "daily":
        return [
            {
                "date": r["obs_date"],
                "level": r["level"],
                "coverage": r["coverage"],
                "low_coverage": bool(r["low_coverage"]),
                "gap_days": r["gap_days"],
                "is_synthetic": bool(r["is_synthetic"]),
            }
            for r in rows
        ]

    # Aggregate to weekly or monthly
    from collections import defaultdict
    buckets: dict[str, list] = defaultdict(list)
    for r in rows:
        if r["level"] is None:
            continue
        d = date.fromisoformat(r["obs_date"])
        key = _iso_week(d) if freq == "weekly" else _month_key(d)
        buckets[key].append({
            "level": r["level"],
            "is_synthetic": bool(r["is_synthetic"]),
        })

    result = []
    for period, entries in sorted(buckets.items()):
        levels = [e["level"] for e in entries]
        partial = len(levels) < 3
        geo_mean = math.exp(sum(math.log(l) for l in levels) / len(levels))
        result.append({
            "period": period,
            "level": round(geo_mean, 4),
            "n_days": len(levels),
            "partial": partial,
            "is_synthetic": any(e["is_synthetic"] for e in entries),
        })
    return result


@app.get("/api/items")
def get_items(
    obs_date: str = Query(..., description="YYYY-MM-DD"),
):
    """Return item prices for a specific observation date."""
    try:
        date.fromisoformat(obs_date)
    except ValueError:
        raise HTTPException(status_code=422, detail="obs_date must be YYYY-MM-DD")

    with get_connection() as con:
        rows = con.execute(
            "SELECT * FROM items_daily WHERE obs_date=? ORDER BY route, lead_days, dep_band",
            (obs_date,),
        ).fetchall()

    return [
        {
            "route": r["route"],
            "lead_days": r["lead_days"],
            "dep_band": r["dep_band"],
            "price": r["price"],
            "n_quotes": r["n_quotes"],
            "is_synthetic": bool(r["is_synthetic"]),
        }
        for r in rows
    ]


@app.get("/api/lead-curve")
def get_lead_curve(
    route: str = Query(..., description="route id, e.g. DEL-BOM"),
    from_date: Optional[str] = Query(None, alias="from", description="YYYY-MM-DD"),
    to_date: Optional[str] = Query(None, alias="to", description="YYYY-MM-DD"),
):
    """
    Price against lead_days for each observation day in [from, to].

    Returns one curve per day: [{obs_date, points: [{lead_days, price}]}].
    """
    with get_connection() as con:
        query = "SELECT * FROM items_daily WHERE route=?"
        params: list = [route]
        if from_date:
            query += " AND obs_date >= ?"
            params.append(from_date)
        if to_date:
            query += " AND obs_date <= ?"
            params.append(to_date)
        query += " ORDER BY obs_date, lead_days"
        rows = con.execute(query, params).fetchall()

    from collections import defaultdict
    by_date: dict[str, list] = defaultdict(list)
    is_synth: dict[str, bool] = {}
    for r in rows:
        by_date[r["obs_date"]].append({
            "lead_days": r["lead_days"],
            "dep_band": r["dep_band"],
            "price": r["price"],
        })
        is_synth[r["obs_date"]] = bool(r["is_synthetic"])

    return [
        {"obs_date": d, "points": pts, "is_synthetic": is_synth[d]}
        for d, pts in sorted(by_date.items())
    ]


@app.get("/api/relatives")
def get_relatives(
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
):
    """
    Return item relatives so the frontend can recompute the index
    under different weights.
    """
    with get_connection() as con:
        query = "SELECT * FROM item_relatives"
        params = []
        clauses = []
        if from_date:
            clauses.append("obs_date >= ?")
            params.append(from_date)
        if to_date:
            clauses.append("obs_date <= ?")
            params.append(to_date)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY obs_date"
        rows = con.execute(query, params).fetchall()

    return [
        {
            "obs_date": r["obs_date"],
            "prev_obs_date": r["prev_obs_date"],
            "route": r["route"],
            "lead_days": r["lead_days"],
            "dep_band": r["dep_band"],
            "relative": r["relative"],
            "is_synthetic": bool(r["is_synthetic"]),
        }
        for r in rows
    ]


@app.get("/api/runs")
def get_runs():
    """Return the run history."""
    with get_connection() as con:
        rows = con.execute(
            "SELECT * FROM runs ORDER BY run_date DESC",
        ).fetchall()

    return [
        {
            "id": r["id"],
            "run_date": r["run_date"],
            "started_at": r["started_at"],
            "finished_at": r["finished_at"],
            "status": r["status"],
            "source": r["source"],
            "pages_ok": r["pages_ok"],
            "pages_failed": r["pages_failed"],
            "notes": r["notes"],
        }
        for r in rows
    ]


@app.get("/api/methodology")
def get_methodology():
    """
    Return methodology metadata: weights in use, item rules, base date,
    and which weights are assumptions.
    """
    first_obs = None
    with get_connection() as con:
        row = con.execute(
            "SELECT obs_date FROM index_daily WHERE scope='overall' ORDER BY obs_date LIMIT 1"
        ).fetchone()
        if row:
            first_obs = row["obs_date"]

    return {
        "base_value": cfg.index.base_value,
        "base_date": first_obs,
        "min_coverage": cfg.index.min_coverage,
        "item_rules": {
            "fare_class": cfg.item_rules.fare_class,
            "nonstop_only": cfg.item_rules.nonstop_only,
            "price_statistic": cfg.item_rules.price_statistic,
            "exclude_anomalies": cfg.item_rules.exclude_anomalies,
        },
        "routes": [
            {
                "id": r.id,
                "origin": r.origin,
                "destination": r.destination,
                "weight": r.weight,
                "weight_assumption": True,  # DGCA data not yet used
            }
            for r in cfg.routes
        ],
        "lead_days": [
            {
                "days": ld.days,
                "weight": ld.weight,
                "weight_assumption": True,  # Equal-weight assumption
            }
            for ld in cfg.lead_days
        ],
        "aggregation": {
            "elementary": "Jevons (geometric mean of item relatives in a band)",
            "lead_level": "Weighted geometric mean over lead windows",
            "route_level": "Weighted geometric mean over lead windows (same)",
            "overall_level": "Weighted arithmetic mean of route relatives",
            "chaining": "Chain-linked from base date",
        },
        "reference": "India CPI 2024: Jevons at elementary, Young-type aggregation above",
    }
