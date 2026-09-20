"""
Database layer for APIx.

Creates the SQLite schema and provides small helper functions
for inserting and querying each table.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Generator

from apix.models import (
    IndexPoint,
    Item,
    ItemRelative,
    Quote,
    RawSnapshot,
)

_DEFAULT_DB_PATH = Path(__file__).parent.parent.parent / "data" / "apix.db"

DDL = """\
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date    TEXT    NOT NULL,          -- YYYY-MM-DD
    started_at  TEXT    NOT NULL,
    finished_at TEXT,
    status      TEXT,                      -- ok | partial | failed
    source      TEXT,
    pages_ok    INTEGER DEFAULT 0,
    pages_failed INTEGER DEFAULT 0,
    notes       TEXT
);

CREATE TABLE IF NOT EXISTS raw_responses (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          INTEGER NOT NULL REFERENCES runs(id),
    route           TEXT    NOT NULL,
    travel_date     TEXT    NOT NULL,
    fetched_at      TEXT    NOT NULL,
    url             TEXT,
    http_status     INTEGER,
    robots_allowed  INTEGER NOT NULL,      -- 0 | 1
    body_path       TEXT
);

CREATE TABLE IF NOT EXISTS quotes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id        INTEGER NOT NULL REFERENCES runs(id),
    obs_date      TEXT    NOT NULL,
    source        TEXT    NOT NULL,
    route         TEXT    NOT NULL,
    origin        TEXT    NOT NULL,
    destination   TEXT    NOT NULL,
    travel_date   TEXT    NOT NULL,
    lead_days     INTEGER NOT NULL,
    carrier       TEXT,
    flight_no     TEXT,
    dep_time      TEXT,
    dep_band      TEXT,
    stops         INTEGER DEFAULT 0,
    fare_class    TEXT    DEFAULT 'economy',
    base_fare     REAL,
    taxes         REAL,
    total_fare    REAL,
    sold_out      INTEGER DEFAULT 0,
    parse_ok      INTEGER DEFAULT 1,
    anomaly_flag  INTEGER DEFAULT 0,
    is_synthetic  INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS items_daily (
    obs_date     TEXT    NOT NULL,
    route        TEXT    NOT NULL,
    lead_days    INTEGER NOT NULL,
    dep_band     TEXT    NOT NULL,
    price        REAL    NOT NULL,
    n_quotes     INTEGER NOT NULL,
    is_synthetic INTEGER DEFAULT 0,
    PRIMARY KEY (obs_date, route, lead_days, dep_band)
);

CREATE TABLE IF NOT EXISTS item_relatives (
    obs_date      TEXT    NOT NULL,
    prev_obs_date TEXT    NOT NULL,
    route         TEXT    NOT NULL,
    lead_days     INTEGER NOT NULL,
    dep_band      TEXT    NOT NULL,
    relative      REAL    NOT NULL,
    is_synthetic  INTEGER DEFAULT 0,
    PRIMARY KEY (obs_date, route, lead_days, dep_band)
);

CREATE TABLE IF NOT EXISTS index_daily (
    obs_date     TEXT    NOT NULL,
    scope        TEXT    NOT NULL,   -- overall | route
    route        TEXT,               -- null for overall
    route_key    TEXT    NOT NULL DEFAULT '',  -- '' for overall, else route id
    level        REAL,               -- null when low_coverage
    coverage     REAL    NOT NULL,
    low_coverage INTEGER NOT NULL,
    gap_days     INTEGER DEFAULT 0,
    is_synthetic INTEGER DEFAULT 0,
    PRIMARY KEY (obs_date, scope, route_key)
);
"""


def get_db_path() -> Path:
    """Return the default database path, creating parent dirs if needed."""
    _DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return _DEFAULT_DB_PATH


@contextmanager
def get_connection(db_path: Path | None = None) -> Generator[sqlite3.Connection, None, None]:
    """Yield a database connection with row_factory set to Row."""
    path = db_path or get_db_path()
    con = sqlite3.connect(str(path))
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def init_db(db_path: Path | None = None) -> None:
    """Create tables if they don't already exist."""
    with get_connection(db_path) as con:
        con.executescript(DDL)


# ---------------------------------------------------------------------------
# Run helpers
# ---------------------------------------------------------------------------

def insert_run(con: sqlite3.Connection, run_date: date, source: str) -> int:
    """Insert a new run row and return its id."""
    cur = con.execute(
        "INSERT INTO runs (run_date, started_at, source) VALUES (?, ?, ?)",
        (run_date.isoformat(), datetime.utcnow().isoformat(), source),
    )
    return cur.lastrowid


def finish_run(
    con: sqlite3.Connection,
    run_id: int,
    status: str,
    pages_ok: int,
    pages_failed: int,
    notes: str | None = None,
) -> None:
    """Update a run row with its final status."""
    con.execute(
        """UPDATE runs SET finished_at=?, status=?, pages_ok=?, pages_failed=?, notes=?
           WHERE id=?""",
        (datetime.utcnow().isoformat(), status, pages_ok, pages_failed, notes, run_id),
    )


def get_run_for_date(con: sqlite3.Connection, run_date: date) -> sqlite3.Row | None:
    """Return the most recent run for run_date, or None."""
    return con.execute(
        "SELECT * FROM runs WHERE run_date=? ORDER BY id DESC LIMIT 1",
        (run_date.isoformat(),),
    ).fetchone()


# ---------------------------------------------------------------------------
# Quote helpers
# ---------------------------------------------------------------------------

def insert_quotes(con: sqlite3.Connection, quotes: list[Quote]) -> None:
    """Bulk-insert quotes; sets q.id on each object."""
    for q in quotes:
        cur = con.execute(
            """INSERT INTO quotes
               (run_id, obs_date, source, route, origin, destination,
                travel_date, lead_days, carrier, flight_no, dep_time, dep_band,
                stops, fare_class, base_fare, taxes, total_fare,
                sold_out, parse_ok, anomaly_flag, is_synthetic)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                q.run_id, q.obs_date.isoformat(), q.source, q.route, q.origin,
                q.destination, q.travel_date.isoformat(), q.lead_days,
                q.carrier, q.flight_no, q.dep_time, q.dep_band,
                q.stops, q.fare_class, q.base_fare, q.taxes, q.total_fare,
                int(q.sold_out), int(q.parse_ok), int(q.anomaly_flag), int(q.is_synthetic),
            ),
        )
        q.id = cur.lastrowid


def delete_quotes_for_run(con: sqlite3.Connection, run_id: int) -> None:
    con.execute("DELETE FROM quotes WHERE run_id=?", (run_id,))


def get_quotes_for_date(con: sqlite3.Connection, obs_date: date) -> list[sqlite3.Row]:
    return con.execute(
        "SELECT * FROM quotes WHERE obs_date=?", (obs_date.isoformat(),)
    ).fetchall()


# ---------------------------------------------------------------------------
# Raw response helpers
# ---------------------------------------------------------------------------

def insert_raw_response(con: sqlite3.Connection, snap: RawSnapshot) -> int:
    cur = con.execute(
        """INSERT INTO raw_responses
           (run_id, route, travel_date, fetched_at, url, http_status, robots_allowed, body_path)
           VALUES (?,?,?,?,?,?,?,?)""",
        (
            snap.run_id, snap.route, snap.travel_date.isoformat(),
            snap.fetched_at.isoformat(), snap.url, snap.http_status,
            int(snap.robots_allowed), snap.body_path,
        ),
    )
    return cur.lastrowid


# ---------------------------------------------------------------------------
# Item helpers
# ---------------------------------------------------------------------------

def upsert_items(con: sqlite3.Connection, items: list[Item]) -> None:
    for item in items:
        con.execute(
            """INSERT INTO items_daily
               (obs_date, route, lead_days, dep_band, price, n_quotes, is_synthetic)
               VALUES (?,?,?,?,?,?,?)
               ON CONFLICT(obs_date, route, lead_days, dep_band)
               DO UPDATE SET price=excluded.price, n_quotes=excluded.n_quotes,
                             is_synthetic=excluded.is_synthetic""",
            (
                item.obs_date.isoformat(), item.route, item.lead_days,
                item.dep_band, item.price, item.n_quotes, int(item.is_synthetic),
            ),
        )


def upsert_item_relatives(con: sqlite3.Connection, relatives: list[ItemRelative]) -> None:
    for r in relatives:
        con.execute(
            """INSERT INTO item_relatives
               (obs_date, prev_obs_date, route, lead_days, dep_band, relative, is_synthetic)
               VALUES (?,?,?,?,?,?,?)
               ON CONFLICT(obs_date, route, lead_days, dep_band)
               DO UPDATE SET prev_obs_date=excluded.prev_obs_date,
                             relative=excluded.relative,
                             is_synthetic=excluded.is_synthetic""",
            (
                r.obs_date.isoformat(), r.prev_obs_date.isoformat(),
                r.route, r.lead_days, r.dep_band, r.relative, int(r.is_synthetic),
            ),
        )


def get_items_before(
    con: sqlite3.Connection, obs_date: date, route: str, lead_days: int, dep_band: str
) -> list[sqlite3.Row]:
    """Return item rows for this cell from the last 7 days (exclusive of obs_date)."""
    return con.execute(
        """SELECT * FROM items_daily
           WHERE route=? AND lead_days=? AND dep_band=?
             AND obs_date < ? AND obs_date >= date(?, '-7 days')
           ORDER BY obs_date""",
        (route, lead_days, dep_band, obs_date.isoformat(), obs_date.isoformat()),
    ).fetchall()


# ---------------------------------------------------------------------------
# Index helpers
# ---------------------------------------------------------------------------

def upsert_index_points(con: sqlite3.Connection, points: list[IndexPoint]) -> None:
    for p in points:
        route_key = p.route if p.route is not None else ''
        con.execute(
            """INSERT INTO index_daily
               (obs_date, scope, route, route_key, level, coverage, low_coverage, gap_days, is_synthetic)
               VALUES (?,?,?,?,?,?,?,?,?)
               ON CONFLICT(obs_date, scope, route_key)
               DO UPDATE SET level=excluded.level, coverage=excluded.coverage,
                             low_coverage=excluded.low_coverage, gap_days=excluded.gap_days,
                             is_synthetic=excluded.is_synthetic""",
            (
                p.obs_date.isoformat(), p.scope, p.route, route_key, p.level,
                p.coverage, int(p.low_coverage), p.gap_days, int(p.is_synthetic),
            ),
        )


def get_last_valid_index(
    con: sqlite3.Connection, scope: str, route: str | None, before_date: date
) -> sqlite3.Row | None:
    """Return the most recent non-null index point before before_date."""
    route_key = route if route is not None else ''
    return con.execute(
        """SELECT * FROM index_daily
           WHERE scope=? AND route_key=?
             AND obs_date < ? AND level IS NOT NULL
           ORDER BY obs_date DESC LIMIT 1""",
        (scope, route_key, before_date.isoformat()),
    ).fetchone()


def get_item_relatives_for_date(
    con: sqlite3.Connection, obs_date: date
) -> list[sqlite3.Row]:
    return con.execute(
        "SELECT * FROM item_relatives WHERE obs_date=?", (obs_date.isoformat(),)
    ).fetchall()
