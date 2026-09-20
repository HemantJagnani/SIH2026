"""
Tests for db.py – Phase 1.

Covers: schema creation, insert/query helpers, and idempotency.
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pytest

from apix.db import (
    finish_run,
    get_connection,
    get_run_for_date,
    init_db,
    insert_run,
    upsert_items,
)
from apix.models import Item


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "test.db"
    init_db(path)
    return path


def test_init_creates_tables(db_path):
    """All 6 tables should exist after init_db."""
    expected = {
        "runs", "raw_responses", "quotes",
        "items_daily", "item_relatives", "index_daily",
    }
    with get_connection(db_path) as con:
        rows = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    found = {r["name"] for r in rows}
    assert expected <= found


def test_init_is_idempotent(db_path):
    """Calling init_db twice does not raise."""
    init_db(db_path)  # second call
    test_init_creates_tables(db_path)


def test_insert_and_finish_run(db_path):
    """Insert a run, finish it, and verify the row."""
    with get_connection(db_path) as con:
        run_id = insert_run(con, date(2026, 1, 1), "fixture")
        finish_run(con, run_id, "ok", pages_ok=12, pages_failed=0)

    with get_connection(db_path) as con:
        row = con.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    assert row["status"] == "ok"
    assert row["pages_ok"] == 12
    assert row["source"] == "fixture"


def test_get_run_for_date_missing(db_path):
    """get_run_for_date returns None when no run exists for a date."""
    with get_connection(db_path) as con:
        result = get_run_for_date(con, date(2025, 1, 1))
    assert result is None


def test_upsert_items_idempotent(db_path):
    """Upserting the same item twice updates in-place, no duplicate rows."""
    item = Item(
        obs_date=date(2026, 1, 1),
        route="DEL-BOM",
        lead_days=7,
        dep_band="morning",
        price=5000.0,
        n_quotes=3,
    )
    with get_connection(db_path) as con:
        upsert_items(con, [item])
        item_updated = Item(
            obs_date=date(2026, 1, 1),
            route="DEL-BOM",
            lead_days=7,
            dep_band="morning",
            price=5200.0,
            n_quotes=4,
        )
        upsert_items(con, [item_updated])

    with get_connection(db_path) as con:
        rows = con.execute("SELECT * FROM items_daily").fetchall()
    assert len(rows) == 1
    assert rows[0]["price"] == 5200.0
    assert rows[0]["n_quotes"] == 4
