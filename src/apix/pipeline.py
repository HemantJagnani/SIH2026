"""
Pipeline – Phase 5.

`run(date)` is the top-level function: for each route × lead window,
it fetches, cleans, persists quotes, builds items, computes relatives
and updates the index. The whole function is idempotent: re-running
the same date replaces that date's derived rows.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from pathlib import Path
from statistics import median as stats_median

from apix.clean import clean_quotes
from apix.config import AppConfig, load_config
from apix.db import (
    delete_quotes_for_run,
    finish_run,
    get_connection,
    get_item_relatives_for_date,
    get_last_valid_index,
    get_run_for_date,
    init_db,
    insert_quotes,
    insert_raw_response,
    insert_run,
    upsert_index_points,
    upsert_item_relatives,
    upsert_items,
)
from apix.index_math import (
    aggregate_index,
    aggregate_route_index,
    compute_item_relative,
    item_price,
)
from apix.models import (
    IndexPoint,
    Item,
    ItemRelative,
    Quote,
)
from apix.sources.base import FareSource

logger = logging.getLogger(__name__)


def _get_source(cfg: AppConfig, run_id: int) -> FareSource:
    """Instantiate the configured source."""
    name = cfg.source.name
    if name == "fixture":
        from apix.sources.fixture import FixtureSource
        return FixtureSource(run_id=run_id, user_agent=cfg.source.user_agent)
    if name == "synthetic":
        from apix.sources.synthetic import SyntheticSource
        return SyntheticSource(run_id=run_id)
    if name == "live":
        from apix.compliance import ComplianceGate
        from apix.sources.live import LiveSource
        gate = ComplianceGate(user_agent=cfg.source.user_agent)
        return LiveSource(
            run_id=run_id,
            target_url_template="",  # set in config before enabling live
            compliance_gate=gate,
            user_agent=cfg.source.user_agent,
        )
    if name == "easemytrip":
        from apix.compliance import ComplianceGate
        from apix.sources.easemytrip import EaseMyTripSource
        gate = ComplianceGate(user_agent=cfg.source.user_agent)
        return EaseMyTripSource(
            run_id=run_id,
            compliance_gate=gate,
            user_agent=cfg.source.user_agent,
        )
    raise ValueError(f"Unknown source: {name!r}")


def _build_items(
    quotes: list[Quote],
    cfg: AppConfig,
    obs_date: date | None = None,
) -> list[Item]:
    """Aggregate cleaned quotes into item prices."""
    from collections import defaultdict

    if obs_date is None and quotes:
        obs_date = quotes[0].obs_date
    if obs_date is None:
        from datetime import date as date_type
        obs_date = date_type.today()

    # Group eligible quotes by (route, lead_days, dep_band)
    cells: dict[tuple, list[float]] = defaultdict(list)
    is_synthetic_map: dict[tuple, bool] = {}

    for q in quotes:
        if (
            not q.parse_ok
            or q.sold_out
            or q.total_fare is None
            or q.dep_band is None
            or q.fare_class != cfg.item_rules.fare_class
        ):
            continue
        if cfg.item_rules.nonstop_only and q.stops > 0:
            continue
        if cfg.item_rules.exclude_anomalies and q.anomaly_flag:
            continue
        cell = (q.route, q.lead_days, q.dep_band)
        cells[cell].append(q.total_fare)
        is_synthetic_map[cell] = q.is_synthetic

    items = []
    for (route, lead, band), fares in cells.items():
        price = item_price(fares, cfg.item_rules.price_statistic)
        if price is not None:
            items.append(Item(
                obs_date=obs_date,
                route=route,
                lead_days=lead,
                dep_band=band,
                price=price,
                n_quotes=len(fares),
                is_synthetic=is_synthetic_map.get((route, lead, band), False),
            ))
    return items


def _build_relatives(
    today_items: list[Item],
    con,
) -> list[ItemRelative]:
    """Compute item relatives vs. the previous observation date."""
    from apix.db import get_items_before

    relatives = []
    for item in today_items:
        # Find the previous item price for this cell
        history = get_items_before(
            con, item.obs_date, item.route, item.lead_days, item.dep_band
        )
        if not history:
            continue
        # Most recent prior day
        prev = sorted(history, key=lambda r: r["obs_date"])[-1]
        prev_price = float(prev["price"])
        prev_date = date.fromisoformat(prev["obs_date"])
        relative = compute_item_relative(item.price, prev_price)
        if relative is None:
            continue
        relatives.append(ItemRelative(
            obs_date=item.obs_date,
            prev_obs_date=prev_date,
            route=item.route,
            lead_days=item.lead_days,
            dep_band=item.dep_band,
            relative=relative,
            is_synthetic=item.is_synthetic,
        ))
    return relatives


def _build_index_points(
    obs_date: date,
    relatives: list[ItemRelative],
    con,
    cfg: AppConfig,
) -> list[IndexPoint]:
    """Compute overall and per-route index points."""
    route_weights = {r.id: r.weight for r in cfg.routes}
    lead_weights = {ld.days: ld.weight for ld in cfg.lead_days}
    n_bands = 3  # morning, afternoon, evening

    item_rel_dict: dict[tuple[str, int, str], float] = {
        (r.route, r.lead_days, r.dep_band): r.relative for r in relatives
    }

    points = []

    # ── Overall index ──────────────────────────────────────────────────
    prev_overall = get_last_valid_index(con, "overall", None, obs_date)
    prev_level = float(prev_overall["level"]) if prev_overall else cfg.index.base_value

    # Determine gap_days
    gap_days = 0
    if prev_overall:
        prev_date = date.fromisoformat(prev_overall["obs_date"])
        gap_days = (obs_date - prev_date).days - 1

    level, coverage = aggregate_index(
        item_relatives=item_rel_dict,
        route_weights=route_weights,
        lead_weights=lead_weights,
        prev_level=prev_level,
        min_coverage=cfg.index.min_coverage,
        n_routes=len(cfg.routes),
        n_leads=len(cfg.lead_days),
        n_bands=n_bands,
    )
    is_synth = all(r.is_synthetic for r in relatives) if relatives else False
    points.append(IndexPoint(
        obs_date=obs_date,
        scope="overall",
        route=None,
        level=level,
        coverage=coverage,
        low_coverage=(level is None),
        gap_days=gap_days,
        is_synthetic=is_synth,
    ))

    # ── Per-route index ────────────────────────────────────────────────
    for route_cfg in cfg.routes:
        prev_route = get_last_valid_index(con, "route", route_cfg.id, obs_date)
        prev_r_level = float(prev_route["level"]) if prev_route else cfg.index.base_value
        r_gap = 0
        if prev_route:
            prev_r_date = date.fromisoformat(prev_route["obs_date"])
            r_gap = (obs_date - prev_r_date).days - 1

        r_level, r_coverage = aggregate_route_index(
            item_relatives=item_rel_dict,
            route=route_cfg.id,
            lead_weights=lead_weights,
            prev_level=prev_r_level,
            min_coverage=cfg.index.min_coverage,
            n_leads=len(cfg.lead_days),
            n_bands=n_bands,
        )
        route_synth = all(
            r.is_synthetic for r in relatives if r.route == route_cfg.id
        ) if relatives else False
        points.append(IndexPoint(
            obs_date=obs_date,
            scope="route",
            route=route_cfg.id,
            level=r_level,
            coverage=r_coverage,
            low_coverage=(r_level is None),
            gap_days=r_gap,
            is_synthetic=route_synth,
        ))

    return points


def run(
    run_date: date,
    cfg: AppConfig | None = None,
    db_path: Path | None = None,
) -> dict:
    """
    Run the full pipeline for *run_date*.

    Returns a summary dict: {status, pages_ok, pages_failed, notes}.
    The run is idempotent: re-running the same date replaces that day's rows.
    """
    if cfg is None:
        cfg = load_config()

    init_db(db_path)

    pages_ok = 0
    pages_failed = 0
    notes_parts = []
    all_quotes: list[Quote] = []

    with get_connection(db_path) as con:
        # Check for an existing run for this date and delete its quotes
        existing = get_run_for_date(con, run_date)
        if existing:
            logger.info("Re-running %s; replacing existing run %s", run_date, existing["id"])
            delete_quotes_for_run(con, existing["id"])

        run_id = insert_run(con, run_date, cfg.source.name)
        source = _get_source(cfg, run_id)

        # ── Collect ────────────────────────────────────────────────────
        for route_cfg in cfg.routes:
            for lead_cfg in cfg.lead_days:
                travel_date = run_date + timedelta(days=lead_cfg.days)
                try:
                    quotes, snapshot = source.fetch(
                        route=route_cfg.id,
                        origin=route_cfg.origin,
                        destination=route_cfg.destination,
                        travel_date=travel_date,
                        run_id=run_id,
                    )
                    insert_raw_response(con, snapshot)

                    if not snapshot.robots_allowed:
                        pages_failed += 1
                        notes_parts.append(
                            f"Compliance refused {route_cfg.id} lead={lead_cfg.days}d"
                        )
                        continue

                    # ── Fix obs_date and lead_days on each quote ────────
                    for q in quotes:
                        q.obs_date = run_date
                        q.lead_days = lead_cfg.days

                    # ── Clean ──────────────────────────────────────────
                    cleaned = clean_quotes(quotes, con=con)
                    insert_quotes(con, cleaned)
                    all_quotes.extend(cleaned)
                    pages_ok += 1

                except Exception as exc:
                    logger.error(
                        "Fetch failed for %s lead=%d: %s",
                        route_cfg.id, lead_cfg.days, exc,
                    )
                    pages_failed += 1
                    notes_parts.append(
                        f"Error {route_cfg.id} lead={lead_cfg.days}d: {exc}"
                    )

        # ── Build items ────────────────────────────────────────────────
        items = _build_items(all_quotes, cfg, obs_date=run_date)
        upsert_items(con, items)

        # ── Build relatives ────────────────────────────────────────────
        relatives = _build_relatives(items, con)
        upsert_item_relatives(con, relatives)

        # ── Build index ────────────────────────────────────────────────
        index_points = _build_index_points(run_date, relatives, con, cfg)
        upsert_index_points(con, index_points)

        # ── Finalise run ───────────────────────────────────────────────
        status = "ok" if pages_failed == 0 else ("partial" if pages_ok > 0 else "failed")
        notes = "; ".join(notes_parts) or None
        finish_run(con, run_id, status, pages_ok, pages_failed, notes)

    logger.info(
        "Run %s complete: status=%s pages_ok=%d pages_failed=%d",
        run_date, status, pages_ok, pages_failed,
    )
    return {"status": status, "pages_ok": pages_ok, "pages_failed": pages_failed, "notes": notes}
